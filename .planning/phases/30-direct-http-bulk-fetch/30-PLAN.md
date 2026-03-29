---
phase: 30
plan: 30-PLAN
title: "Direct HTTP Bulk Fetch for get_device_ips()"
wave: 1
depends_on: []
files_modified:
  - nautobot_mcp/ipam.py
  - tests/test_ipam.py [NEW]
autonomous: true
requirements_addressed: [URI-01, URI-02, URI-03, URI-04, URI-05, URI-06]
---

<objective>
Replace all .filter(interface=chunk) and .filter(id__in=chunk) loops in ipam.py get_device_ips() with O(1) direct HTTP calls using DRF comma-separated UUID format, with automatic next-link pagination and return_obj() wrapping. Covers Pass 2 (M2M) and Pass 3 (IP detail) only. Pass 1 (interface fetch) is unchanged.
</objective>

<must_haves>
- _bulk_get_by_ids() helper at module level in ipam.py -- empty ID list returns [] immediately, no HTTP call
- Pass 2 in get_device_ips() replaced with single direct HTTP call to /api/ipam/ip_address_to_interface/?interface=uuid1,uuid2,...
- Pass 3 in get_device_ips() replaced with single direct HTTP call to /api/ipam/ip_addresses/?id__in=uuid1,uuid2,...
- Both passes follow next links when present in HTTP response body
- Both passes wrap raw HTTP results with endpoint.return_obj() before returning
- Pass 3 partial-failure: IPs missing from server response are added to unlinked_ips as IPAddressSummary stubs
- Unit tests: normal device with IPs, device with no IPs, device with > 500 IPs (mocked HTTP)
</must_haves>

---

## Task 1: Extract _bulk_get_by_ids() helper

<read_first>
- nautobot_mcp/ipam.py (lines 318-407 -- current get_device_ips() implementation)
- nautobot_mcp/client.py (lines 161-200 -- client.api.http_session, client._profile.url)
- .planning/phases/30-direct-http-bulk-fetch/30-RESEARCH.md section 5 -- exact helper signature and flow
</read_first>

<action>
Add _bulk_get_by_ids() as a module-level function at the top of ipam.py, BEFORE list_prefixes(). It must:

1. Accept (client, endpoint, ids, id_param) -- matching D-09 from 30-CONTEXT.md
2. If ids is empty, return [] immediately (no HTTP call -- URI-05 / D-03)
3. Build URL: f"{client._profile.url}{endpoint.url}" where endpoint.url is the DRF path (e.g. "/api/ipam/ip_addresses/")
4. Build params: {id_param: ",".join(ids)} -- requests serializes this as ?interface=uuid1,uuid2,... or ?id__in=uuid1,uuid2,...
5. Fetch the first page: client.api.http_session.get(url, params=params)
6. Raise for status via resp.raise_for_status() -- propagates to _handle_api_error at the caller level (D-11)
7. Collect results and follow next links: while data.get("next"): resp = client.api.http_session.get(next_url); collect data["results"]; update next_url
8. Wrap all collected raw dicts with endpoint.return_obj(r, client.api, endpoint) -- pure constructor, no HTTP call (D-08)
9. Return the list of pynautobot Record objects

Type annotation: Use TYPE_CHECKING guard, import Endpoint from pynautobot.core.endpoint, annotate client and endpoint. Return type is list (no specific element type -- matches existing codebase style).

The next_url variable: declare next_url: str | None = None before the loop, then inside the loop assign after each request. First iteration: results is empty so use url + params; subsequent iterations: use next_url directly with params=None.
</action>

<acceptance_criteria>
- python -c "from nautobot_mcp.ipam import _bulk_get_by_ids" exits 0
- _bulk_get_by_ids(client, endpoint, [], "id__in") returns [] without making any HTTP call
- _bulk_get_by_ids(client, endpoint, ["uuid1"], "interface") makes exactly 1 HTTP GET call with params={"interface": "uuid1"}
- _bulk_get_by_ids(client, endpoint, ["uuid1","uuid2"], "id__in") makes exactly 1 HTTP GET call with params={"id__in": "uuid1,uuid2"}
- When response has next link, function follows it and makes additional requests until next is null
- Return value is a list of pynautobot Record objects (not raw dicts)
</acceptance_criteria>

---

## Task 2: Replace Pass 2 and Pass 3 in get_device_ips() with direct HTTP

<read_first>
- nautobot_mcp/ipam.py (lines 318-407 -- current get_device_ips())
- nautobot_mcp/ipam.py (lines 118-140 -- existing direct HTTP + return_obj() pattern in list_ip_addresses())
- .planning/phases/30-direct-http-bulk-fetch/30-CONTEXT.md (D-01 through D-12)
</read_first>

<action>
In get_device_ips(), replace the Pass 2 chunked .filter() loop:

OLD:
  CHUNK = 500
  m2m_records: list = []
  for chunk in chunked(iface_ids, CHUNK):
      chunk_records = list(
          client.api.ipam.ip_address_to_interface.filter(interface=chunk)
      )
      m2m_records.extend(chunk_records)

NEW:
  m2m_records: list = _bulk_get_by_ids(
      client,
      client.api.ipam.ip_address_to_interface,
      iface_ids,
      id_param="interface",
  )

Then replace the Pass 3 chunked .filter() loop:

OLD:
  ip_map: dict = {}
  for chunk in chunked(ip_ids, CHUNK):
      for ip in client.api.ipam.ip_addresses.filter(id__in=chunk):
          ip_map[str(ip.id)] = ip

NEW:
  ip_records: list = _bulk_get_by_ids(
      client,
      client.api.ipam.ip_addresses,
      ip_ids,
      id_param="id__in",
  )
  ip_map = {str(ip.id): ip for ip in ip_records}

Remove from nautobot_mcp.utils import chunked from the function body -- it is no longer used in get_device_ips() after the refactor. The chunked import at module level is fine to keep (still used in list_vlans()).

Pass 3 partial failure -- unlinked_ips population (D-12):
After fetching ip_records, compute missing IDs and add them to unlinked_ips as IPAddressSummary stubs:

  # Track IPs that exist in M2M but are no longer in Nautobot (deleted between Pass 2 and 3)
  fetched_ids = {str(ip.id) for ip in ip_records}
  requested_ids = set(ip_ids)
  missing_ip_ids = requested_ids - fetched_ids

  unlinked_ips: list[IPAddressSummary] = []
  if missing_ip_ids:
      for missing_id in missing_ip_ids:
          unlinked_ips.append(IPAddressSummary(
              id=missing_id,
              address="<deleted>",
              status="Unknown",
              namespace=None,
              tenant=None,
              dns_name=None,
              type="Host",
          ))

Empty IP ID list early return (D-06): After collecting ip_ids from M2M results, if the list is empty, return immediately without calling Pass 3:

  if not ip_ids:
      return DeviceIPsResponse(
          device_name=device_name,
          total_ips=0,
          interface_ips=[],
          unlinked_ips=[],
      )

Update the final return to pass unlinked_ips instead of the hardcoded [].

IMPORTANT: unlinked_ips is typed as list[IPAddressSummary] in DeviceIPsResponse. The stub uses IPAddressSummary with placeholder values. This is correct per the model definition.
</action>

<acceptance_criteria>
- uv run pytest tests/test_ipam.py -v passes all new tests
- uv run pytest tests/test_drift.py -v still passes (verify get_device_ips interface unchanged)
- python -c "from nautobot_mcp.ipam import get_device_ips" exits 0
- Pass 2 makes 1 HTTP GET to ip_address_to_interface/?interface=... (comma-separated), not N .filter() calls
- Pass 3 makes 1 HTTP GET to ip_addresses/?id__in=... (comma-separated), not N .filter() calls
- When ip_ids is empty, Pass 3 is skipped entirely
- When M2M returns 0 records, function returns early with empty interface_ips
- Missing IP IDs (stale UUIDs) appear in response.unlinked_ips as IPAddressSummary stubs
- The DeviceIPsResponse return type is unchanged -- no call sites are broken
</acceptance_criteria>

---

## Task 3: Add unit tests for get_device_ips() bulk fetch

<read_first>
- tests/test_drift.py (lines 118-251 -- existing get_device_ips mocking pattern)
- nautobot_mcp/models/ipam.py (DeviceIPsResponse, DeviceIPEntry, IPAddressSummary)
- nautobot_mcp/ipam.py (refactored get_device_ips())
</read_first>

<action>
Create tests/test_ipam.py with pytest. Use unittest.mock.MagicMock to mock client.api.http_session.get() for full control over response shape. Do NOT make live HTTP calls.

Test class: TestBulkGetByIds

test_empty_ids_returns_early:
- Call _bulk_get_by_ids(client, endpoint, [], "id__in")
- Assert: returns [], http_session.get was never called

test_single_page_fetches_all_results:
- Mock http_session.get returning {"results": [{"id": "uuid1", "url": "/api/ipam/ip_addresses/uuid1/"}, {"id": "uuid2", "url": "/api/ipam/ip_addresses/uuid2/"}], "next": None}
- Call with ["uuid1", "uuid2"] and id_param="id__in"
- Assert: exactly 1 HTTP call, params={"id__in": "uuid1,uuid2"}, returns 2 wrapped Records

test_pagination_follows_next_link:
- Mock two sequential responses:
  - Page 1: 2 results + next pointing to page 2 URL
  - Page 2: 1 result + next: None
- Assert: 2 HTTP calls total, all 3 results returned

test_uses_comma_separated_format:
- Patch http_session.get and capture call_args
- Call with 3 UUIDs
- Assert: captured params dict has "id__in": "uuid1,uuid2,uuid3" (comma-joined string, not a list)

Test class: TestGetDeviceIPs

test_normal_device_with_ips:
- Mock Pass 1 (interfaces): 2 interfaces
- Mock Pass 2 (M2M): 3 M2M records linking those interfaces to 3 IPs
- Mock Pass 3 (IP detail): 3 IP records
- Assert DeviceIPsResponse has total_ips=3, len(interface_ips)=3
- Assert unlinked_ips is empty

test_device_with_no_interfaces:
- Mock Pass 1: empty interface list
- Assert returns DeviceIPsResponse with total_ips=0, interface_ips=[], unlinked_ips=[]

test_device_with_no_ips:
- Mock Pass 1: 1 interface with name "ge-0/0/0"
- Mock Pass 2: empty M2M results
- Assert returns immediately after empty ip_ids check (Pass 3 skipped)

test_device_with_more_than_500_ips (D-04 / no chunking fallback):
- Mock 501 interface UUIDs
- Mock Pass 2 M2M returning 501 M2M records
- Mock Pass 3 IP detail returning all 501 IPs (single comma-separated request)
- Assert: only 1 HTTP call to Pass 3 endpoint (no chunking fallback), total_ips=501

test_partial_failure_stale_ips_in_unlinked_ips:
- M2M returns 3 IPs (uuid1, uuid2, uuid3)
- Pass 3 only returns 2 IPs (uuid1, uuid3) -- uuid2 is missing (stale)
- Assert: unlinked_ips has 1 entry with id=uuid2, address="<deleted>"
- Assert: interface_ips has 2 entries (uuid1, uuid3 only)

test_http_error_propagates:
- Mock http_session.get raising requests.exceptions.HTTPError (500)
- Assert: NautobotAPIError is raised (via _handle_api_error)

For all mocks, set mock_resp.raise_for_status = MagicMock() (no-op) and mock_resp.ok = True unless testing the error case. Use side_effect to simulate pagination with sequential responses.
</action>

<acceptance_criteria>
- uv run pytest tests/test_ipam.py -v exits 0 with all tests passing
- Each test is isolated (no shared mutable state)
- Mock assertions verify exact params passed to http_session.get
- The test_device_with_more_than_500_ips test confirms no per-chunk HTTP calls are made -- one bulk request only
- No live HTTP calls are made in any test (no requests real network access)
- tests/test_drift.py still passes after refactor (interface unchanged)
</acceptance_criteria>

---

## Verification Checklist

After all tasks are complete, run:

  # Unit tests
  uv run pytest tests/test_ipam.py tests/test_drift.py -v

  # Import smoke
  python -c "from nautobot_mcp.ipam import get_device_ips, _bulk_get_by_ids; print('OK')"

Criterion mapping:

| # | Criterion | How Verified |
|---|-----------|--------------|
| 1 | Both passes use http_session.get() -- no .filter() loops | Code inspection + mock assertion |
| 2 | Comma-separated ?interface=... and ?id__in=... format | Mock call_args capture in tests |
| 3 | Pagination via next links | test_pagination_follows_next_link |
| 4 | return_obj() wrapping -- pynautobot Record output | test_single_page_fetches_all_results checks Record type |
| 5 | Empty ID sets skip HTTP call | test_empty_ids_returns_early |
| 6 | > 500 IPs handled in 1 request | test_device_with_more_than_500_ips |
