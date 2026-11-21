"""Local, evidence-preserving rental research. Python standard library only."""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import io
import json
import math
import os
from pathlib import Path
import tempfile
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

VERSION = "1.0.0"
KINDS = {"entire_flat", "female_room", "male_room", "private_room"}
STATUSES = {"none", "sent", "delivered", "read", "unknown", "closed", "held"}
DISPOSITIONS = {"active", "historical", "held", "closed", "unavailable"}
PROTECTED = STATUSES - {"none"}
MAX_BYTES = 4_000_000


class ValidationError(ValueError):
    pass


def text(value, field, limit=4000, required=False):
    if not isinstance(value, str) or len(value) > limit or (required and not value.strip()):
        raise ValidationError(f"Invalid {field}")
    return value.strip()


def number(value, field, minimum=0, maximum=100_000_000, nullable=True):
    if value is None and nullable:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValidationError(f"Invalid number: {field}")
    if not minimum <= value <= maximum:
        raise ValidationError(f"Out of range: {field}")
    return value


def safe_url(value, nullable=True):
    if value in (None, "") and nullable:
        return None
    value = text(value, "URL", required=True)
    try:
        parsed = urlsplit(value)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError()
        if parsed.port not in (None, 443) or any(c.isspace() or ord(c) < 32 or c in '<>"`' for c in value):
            raise ValueError()
    except (ValueError, TypeError):
        raise ValidationError("Only credential-free HTTPS source URLs are accepted") from None
    return value


def canonical_url(value):
    parsed = urlsplit(safe_url(value, False))
    query = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True)
             if not k.startswith(("utm_", "__")) and k not in {"fbclid", "gclid", "ref"}]
    return urlunsplit(("https", parsed.netloc.lower().removeprefix("www."),
                       parsed.path.rstrip("/") or "/", urlencode(sorted(query)), ""))


def iso_date(value, field):
    try:
        return dt.date.fromisoformat(value).isoformat()
    except (TypeError, ValueError):
        raise ValidationError(f"{field} must be an explicit YYYY-MM-DD date") from None


def timestamp(value, field, nullable=True):
    if not value and nullable:
        return None
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError()
        return parsed.isoformat()
    except (AttributeError, TypeError, ValueError):
        raise ValidationError(f"{field} must have a timezone") from None


def point(value):
    if not isinstance(value, dict):
        raise ValidationError("Coordinates must be an object")
    return {"lat": number(value.get("lat"), "latitude", -90, 90, False),
            "lng": number(value.get("lng"), "longitude", -180, 180, False)}


def string_list(value, field):
    if not isinstance(value, list) or len(value) > 200:
        raise ValidationError(f"Invalid {field}")
    return [text(x, field, 500, True) for x in value]


def validate_profile(raw):
    if not isinstance(raw, dict):
        raise ValidationError("Profile must be an object")
    profile = {
        "schema_version": 1,
        "name": text(raw.get("name", "My rental search"), "name", 120, True),
        "city": text(raw.get("city"), "city", 120, True),
        "currency": text(raw.get("currency", "INR"), "currency", 8, True),
        "timezone": text(raw.get("timezone", "UTC"), "timezone", 80, True),
        "monthly_limit": number(raw.get("monthly_limit"), "monthly limit", 1, nullable=False),
        "strict_monthly_limit": raw.get("strict_monthly_limit", True) is not False,
        "move_in_before": iso_date(raw.get("move_in_before"), "move-in deadline"),
        "prefer_radius_m": number(raw.get("prefer_radius_m", 1000), "preferred radius", 1, 100000, False),
        "max_radius_m": number(raw.get("max_radius_m", 2000), "maximum radius", 1, 100000, False),
        "freshness_hours": number(raw.get("freshness_hours", 48), "freshness hours", 1, 8760, False),
        "accepted_kinds": string_list(raw.get("accepted_kinds", ["entire_flat"]), "accepted kinds"),
        "excluded_areas": string_list(raw.get("excluded_areas", []), "excluded areas"),
        "held_source_urls": [safe_url(x, False) for x in raw.get("held_source_urls", [])],
        "search_terms": string_list(raw.get("search_terms", []), "search terms"),
        "references": string_list(raw.get("references", []), "references"),
        "source_priority": string_list(raw.get("source_priority", ["facebook", "housing", "nobroker"]), "source priority"),
        "room_anchor_ids": string_list(raw.get("room_anchor_ids", []), "room anchors"),
        "unverified_anchors": string_list(raw.get("unverified_anchors", []), "unverified anchors"),
        "demo": raw.get("demo") is True,
        "anchors": [],
    }
    if not set(profile["accepted_kinds"]) <= KINDS:
        raise ValidationError("Unsupported housing kind")
    try:
        ZoneInfo(profile["timezone"])
    except (ValueError, ZoneInfoNotFoundError):
        raise ValidationError("Unknown IANA timezone") from None
    if profile["prefer_radius_m"] > profile["max_radius_m"]:
        raise ValidationError("Preferred radius exceeds maximum radius")
    anchors = raw.get("anchors", [])
    if not isinstance(anchors, list) or len(anchors) > 20:
        raise ValidationError("Invalid anchors")
    ids = set()
    for a in anchors:
        anchor = {"id": text(a.get("id"), "anchor id", 80, True),
                  "name": text(a.get("name"), "anchor name", 160, True),
                  **point(a), "verified": a.get("verified") is True,
                  "access_confirmed": a.get("access_confirmed") is True,
                  "source_url": safe_url(a.get("source_url"))}
        if anchor["id"] in ids:
            raise ValidationError("Duplicate anchor id")
        ids.add(anchor["id"])
        profile["anchors"].append(anchor)
    if not set(profile["room_anchor_ids"]) <= ids:
        raise ValidationError("Room anchor id is not defined")
    return profile


def validate_listing(raw):
    if not isinstance(raw, dict):
        raise ValidationError("Listing must be an object")
    source = safe_url(raw.get("source_url"), False)
    listing = {
        "id": text(raw.get("id") or hashlib.sha256(canonical_url(source).encode()).hexdigest()[:16], "listing id", 100, True),
        "title": text(raw.get("title"), "listing title", 240, True),
        "kind": text(raw.get("kind"), "kind", 40, True),
        "area": text(raw.get("area", ""), "area", 400),
        "source_url": source,
        "source_platform": text(raw.get("source_platform", urlsplit(source).hostname), "platform", 80),
        "source_checked_at": timestamp(raw.get("source_checked_at"), "source checked time"),
        "advertised_availability": text(raw.get("advertised_availability", "Not stated"), "availability", 500),
        "rent": number(raw.get("rent"), "rent"),
        "maintenance": number(raw.get("maintenance"), "maintenance"),
        "maintenance_included": raw.get("maintenance_included") is True,
        "deposit": number(raw.get("deposit"), "deposit"),
        "brokerage": number(raw.get("brokerage"), "brokerage"),
        "setup_cost": number(raw.get("setup_cost"), "setup cost"),
        "furnishing": text(raw.get("furnishing", "Not confirmed"), "furnishing", 120),
        "size_sqft": number(raw.get("size_sqft"), "size"),
        "notes": text(raw.get("notes", ""), "notes", 5000),
        "disposition": raw.get("disposition", "active"),
        "demo": raw.get("demo") is True,
        "coordinates": None, "walk": None,
    }
    if listing["kind"] not in KINDS or listing["disposition"] not in DISPOSITIONS:
        raise ValidationError("Invalid kind or disposition")
    if raw.get("coordinates") is not None:
        c = raw["coordinates"]
        precision = c.get("precision", "advertised_area")
        if precision not in {"advertised_area", "building", "entrance"}:
            raise ValidationError("Invalid coordinate precision")
        listing["coordinates"] = {**point(c), "precision": precision, "source_url": safe_url(c.get("source_url"))}
    if raw.get("walk") is not None:
        w = raw["walk"]
        status = w.get("status", "estimate")
        if status not in {"estimate", "verified"}:
            raise ValidationError("Invalid walk status")
        listing["walk"] = {
            "anchor_id": text(w.get("anchor_id"), "walk anchor", 80, True),
            "metres": number(w.get("metres"), "walking distance"),
            "minutes": number(w.get("minutes"), "walking time"),
            "status": status, "exact_entrance": w.get("exact_entrance") is True,
            "legitimate": w.get("legitimate") is True,
            "source_url": safe_url(w.get("source_url")),
            "checked_at": timestamp(w.get("checked_at"), "walk checked time"),
            "restriction_note": text(w.get("restriction_note", ""), "route restriction", 1000),
        }
    a = raw.get("availability", {})
    if not isinstance(a, dict) or a.get("status", "unconfirmed") not in {"unconfirmed", "confirmed", "unavailable"}:
        raise ValidationError("Invalid availability status")
    listing["availability"] = {"status": a.get("status", "unconfirmed"),
        "before_deadline": a.get("before_deadline") if isinstance(a.get("before_deadline"), bool) else None,
        "confirmed_at": timestamp(a.get("confirmed_at"), "availability confirmed time"),
        "evidence_url": safe_url(a.get("evidence_url")),
        "evidence_note": text(a.get("evidence_note", ""), "availability evidence", 1000)}
    c = raw.get("contact", {})
    if not isinstance(c, dict) or c.get("status", "none") not in STATUSES:
        raise ValidationError("Invalid contact status")
    phone = c.get("phone")
    if phone is not None:
        phone = text(phone, "phone", 20, True)
        if not phone.startswith("+") or not phone[1:].isdigit() or not 8 <= len(phone[1:]) <= 15:
            raise ValidationError("Phone must be normalized international format")
    listing["contact"] = {"phone": phone, "provenance_url": safe_url(c.get("provenance_url")),
        "role": text(c.get("role", "unverified"), "contact role", 80),
        "status": c.get("status", "none"), "channel": text(c.get("channel", ""), "channel", 40),
        "recipient_verified": c.get("recipient_verified") is True,
        "history_checked_at": timestamp(c.get("history_checked_at"), "history checked time"),
        "last_action_at": timestamp(c.get("last_action_at"), "last contact time"),
        "messenger_url": safe_url(c.get("messenger_url")),
        "evidence_note": text(c.get("evidence_note", ""), "contact evidence", 1500)}
    return listing


def read_json(path):
    path = Path(path)
    if path.stat().st_size > MAX_BYTES:
        raise ValidationError("JSON input exceeds 4 MB")
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, tmp = tempfile.mkstemp(prefix=".flat-finder-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def distance_m(a, b):
    lat1, lat2 = math.radians(a["lat"]), math.radians(b["lat"])
    delta_lat, delta_lng = lat2 - lat1, math.radians(b["lng"] - a["lng"])
    h = math.sin(delta_lat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lng / 2) ** 2
    return 6371008.8 * 2 * math.asin(min(1, math.sqrt(h)))


def age_hours(value, now):
    if not value:
        return None
    return (now - dt.datetime.fromisoformat(value)).total_seconds() / 3600


def assess(listing, profile, now=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    reasons, gaps = [], []
    total = None if listing["rent"] is None else (listing["rent"] if listing["maintenance_included"]
             else None if listing["maintenance"] is None else listing["rent"] + listing["maintenance"])
    if total is None:
        gaps.append("Rent plus maintenance is not fully known")
    elif (total >= profile["monthly_limit"] if profile["strict_monthly_limit"] else total > profile["monthly_limit"]):
        reasons.append("Over the saved monthly rent-plus-maintenance limit")
    if listing["kind"] not in profile["accepted_kinds"]:
        reasons.append("Housing type does not match the saved profile")
    if any(x.casefold() in listing["area"].casefold() for x in profile["excluded_areas"]):
        reasons.append("Explicitly excluded area")
    held = listing["disposition"] in {"held", "historical"} or canonical_url(listing["source_url"]) in {
        canonical_url(x) for x in profile["held_source_urls"]}
    closed = listing["disposition"] == "closed" or listing["contact"]["status"] == "closed"
    if listing["contact"]["status"] == "held":
        held = True
    if listing["disposition"] == "unavailable" or listing["availability"]["status"] == "unavailable":
        reasons.append("Reported unavailable")
    deadline_passed = now.astimezone(ZoneInfo(profile["timezone"])).date() >= dt.date.fromisoformat(profile["move_in_before"])
    if deadline_passed:
        gaps.append("Saved move-in window has passed; ask for an updated window once")
    anchors = [a for a in profile["anchors"] if a["verified"]]
    if listing["kind"] != "entire_flat" and profile["room_anchor_ids"]:
        anchors = [a for a in anchors if a["id"] in profile["room_anchor_ids"]]
    distances = [(distance_m(listing["coordinates"], a), a) for a in anchors] if listing["coordinates"] else []
    nearest = min(distances, key=lambda x: x[0]) if distances else None
    radius = round(nearest[0]) if nearest else None
    if radius is None:
        gaps.append("No verified property-point / commute-anchor pair")
    elif radius > profile["max_radius_m"]:
        reasons.append("Outside the radius of currently verified commute anchors")
    w = listing["walk"]
    valid_anchor = next((a for a in anchors if w and a["id"] == w["anchor_id"] and a["access_confirmed"]), None)
    if not (w and valid_anchor and w["status"] == "verified" and w["legitimate"] and w["exact_entrance"]
            and listing["coordinates"] and listing["coordinates"]["precision"] == "entrance"
            and w["source_url"] and w["checked_at"] and 0 <= age_hours(w["checked_at"], now) <= profile["freshness_hours"]):
        gaps.append("Practical walk from the actual entrance is not verified")
    a = listing["availability"]
    availability_age = age_hours(a["confirmed_at"], now)
    if a["status"] == "confirmed" and a["before_deadline"] is False:
        reasons.append("Confirmed availability misses the saved deadline")
    elif not (a["status"] == "confirmed" and a["before_deadline"] is True and a["confirmed_at"]
              and (a["evidence_url"] or a["evidence_note"]) and availability_age is not None
              and 0 <= availability_age <= profile["freshness_hours"]):
        gaps.append("Current availability before the deadline is not confirmed")
    source_age = age_hours(listing["source_checked_at"], now)
    if source_age is None or source_age < 0 or source_age > profile["freshness_hours"]:
        gaps.append("Source needs a fresh check")
    if "/search/" in urlsplit(listing["source_url"]).path:
        gaps.append("Exact listing permalink is missing")
    if profile["demo"] or listing["demo"]:
        gaps.append("Synthetic demo data, not a real rental offer")
    state = "closed" if closed else "held" if held else "excluded" if reasons else "provisional" if gaps else "ready"
    status = listing["contact"]["status"]
    if closed or held or reasons or deadline_passed:
        action = "Do not initiate contact"
    elif status == "unknown":
        action = "Reconcile the earlier delivery outcome; do not retry"
    elif status in {"sent", "delivered", "read"}:
        action = "Await a substantive reply; do not repeat the request"
    else:
        action = "Verify account, recipient and full current history before a first contextual enquiry"
    return {"state": state, "monthly_total": total, "radius_m": radius,
            "nearest_anchor": nearest[1]["name"] if nearest else None,
            "preferred_radius": radius is not None and radius <= profile["prefer_radius_m"],
            "reasons": reasons, "gaps": gaps, "next_action": action,
            "can_prepare_contact": not (closed or held or reasons or deadline_passed or status in PROTECTED)
                                   and not (profile["demo"] or listing["demo"]),
            "source_age_hours": round(source_age, 1) if source_age is not None else None}


def workspace_state(workspace, now=None):
    workspace = Path(workspace)
    profile = validate_profile(read_json(workspace / "profile.json"))
    data = read_json(workspace / "listings.json")
    if not isinstance(data, dict) or not isinstance(data.get("listings"), list) or len(data["listings"]) > 5000:
        raise ValidationError("Dataset must contain at most 5,000 listings")
    now = now or dt.datetime.now(dt.timezone.utc)
    rows = []
    for raw in data["listings"]:
        listing = validate_listing(raw)
        listing["assessment"] = assess(listing, profile, now)
        rows.append(listing)
    for listing in rows:
        contact = listing["contact"]
        if not listing["assessment"]["can_prepare_contact"]:
            continue
        conflicts = [old for old in rows if old is not listing and old["contact"]["status"] in PROTECTED
                     and ((contact["phone"] and contact["phone"] == old["contact"]["phone"])
                          or (contact["messenger_url"] and old["contact"]["messenger_url"]
                              and canonical_url(contact["messenger_url"]) == canonical_url(old["contact"]["messenger_url"])))]
        if conflicts:
            listing["assessment"]["can_prepare_contact"] = False
            listing["assessment"]["next_action"] = "Reconcile protected contact history on another saved source; do not send a duplicate"
            listing["assessment"]["gaps"].append("Same phone or Messenger recipient already has a protected contact record")
            if listing["assessment"]["state"] == "ready":
                listing["assessment"]["state"] = "provisional"
    priority = {"ready": 0, "provisional": 1, "held": 2, "excluded": 3, "closed": 4}
    rows.sort(key=lambda x: (priority[x["assessment"]["state"]],
                            x["assessment"]["radius_m"] if x["assessment"]["radius_m"] is not None else float("inf"), x["title"]))
    events = data.get("events", [])
    access = data.get("access", [])
    if not isinstance(events, list) or not isinstance(access, list):
        raise ValidationError("Invalid research log or access states")
    clean_events = [{"at": timestamp(e.get("at"), "event time"),
                     "title": text(e.get("title", "Research update"), "event title", 300),
                     "detail": text(e.get("detail", ""), "event detail", 1500),
                     "source_url": safe_url(e.get("source_url"))} for e in events[:100]]
    clean_access = [{"channel": text(e.get("channel", ""), "channel", 80),
                     "state": text(e.get("state", "unverified"), "access state", 100),
                     "detail": text(e.get("detail", ""), "access detail", 1500),
                     "checked_at": timestamp(e.get("checked_at"), "access check")} for e in access[:20]]
    return {"version": VERSION, "generated_at": now.isoformat(), "profile": profile, "listings": rows,
            "counts": {s: sum(x["assessment"]["state"] == s for x in rows) for s in priority},
            "events": clean_events, "access": clean_access,
            "limitations": "Imported source evidence is not a live search or delivery receipt. Radius is not walking distance."}


def merge_listings(existing, incoming):
    result = [validate_listing(x) for x in existing]
    for raw in incoming:
        candidate = validate_listing(raw)
        key = canonical_url(candidate["source_url"])
        match = next((i for i, old in enumerate(result) if canonical_url(old["source_url"]) == key), None)
        if match is None:
            if any(x["id"] == candidate["id"] for x in result):
                raise ValidationError("Listing id already belongs to a different source")
            result.append(candidate)
            continue
        old = result[match]
        candidate["id"] = old["id"]
        if old["contact"]["status"] in PROTECTED and candidate["contact"]["status"] == "none":
            candidate["contact"] = old["contact"]
        if old["disposition"] in {"closed", "held", "unavailable"}:
            candidate["disposition"] = old["disposition"]
        if old["contact"]["status"] in {"closed", "held", "unknown"}:
            candidate["contact"] = old["contact"]
        result[match] = candidate
    return result


def search_plan(state):
    p = state["profile"]
    queries = []
    terms = p["references"] + p["search_terms"]
    for term in dict.fromkeys(terms):
        queries.append({"query": f"{term} rent", "platform": "facebook",
                        "url": "https://www.facebook.com/search/posts/?" + urlencode({"q": f"{term} rent"}),
                        "state": "unreviewed", "purpose": "Find actual matching posts; compare building, photos, costs and pin"})
    for platform in p["source_priority"]:
        if platform != "facebook":
            for term in p["search_terms"]:
                queries.append({"query": f"{term} rent {platform}", "platform": platform,
                                "state": "unreviewed", "purpose": "Use the site's current search UI or available web search"})
    return {"created_at": state["generated_at"], "profile_name": p["name"],
            "deadline": p["move_in_before"], "tasks": queries,
            "contacts": [{"id": x["id"], "title": x["title"], "source_url": x["source_url"],
                          "next_action": x["assessment"]["next_action"],
                          "preflight_candidate": x["assessment"]["can_prepare_contact"]} for x in state["listings"]],
            "permission": "A plan is not a search, a send or permission to send. Apply the user's actual scoped authority and live history checks."}


def money(value, currency="INR"):
    if value is None:
        return "Unknown"
    return ("₹" if currency == "INR" else currency + " ") + format(value, ",.0f")


def markdown_report(state, include_held=False):
    p = state["profile"]
    lines = [f"**{p['name']}** — checked data as of {state['generated_at'][:10]}", "",
             f"Rent + maintenance {'strictly below' if p['strict_monthly_limit'] else 'at most'} {money(p['monthly_limit'], p['currency'])}; move-in before {p['move_in_before']}. "
             f"Search radius {p['max_radius_m'] / 1000:g} km; actual walking route checked separately.", "",
             "| Property / source | Monthly total | Deposit / other costs | Commute evidence | Status / next step |",
             "|---|---:|---|---|---|"]
    def esc(value):
        return str(value).replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]").replace("|", "\\|").replace("\n", " ").replace("<", "&lt;").replace(">", "&gt;")
    for x in state["listings"]:
        a = x["assessment"]
        if not include_held and a["state"] not in {"ready", "provisional"}:
            continue
        walk = x["walk"]
        route = (f"{walk['metres']:g} m / {walk['minutes']:g} min ({walk['status']})" if walk and walk["metres"] is not None and walk["minutes"] is not None else "Walk unverified")
        costs = f"Deposit {money(x['deposit'], p['currency'])}; brokerage {money(x['brokerage'], p['currency'])}; setup {money(x['setup_cost'], p['currency'])}"
        status = f"{a['state']}; contact: {x['contact']['status']}. {a['next_action']}. " + "; ".join(a["reasons"] + a["gaps"])
        link = x['source_url'].replace('(', '%28').replace(')', '%29')
        lines.append(f"| [{esc(x['title'])}]({link}) | {money(a['monthly_total'], p['currency'])} | {esc(costs)} | {esc(route)} | {esc(status)} |")
    lines += ["", "Ad prices and advertised dates are separate from current provider confirmation. Source / map links are evidence to inspect, not guarantees."]
    return "\n".join(lines) + "\n"


def csv_report(state):
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["title", "source", "kind", "monthly_total", "deposit", "radius_m", "status", "contact_status", "gaps"])
    for x in state["listings"]:
        a = x["assessment"]
        row = [x["title"], x["source_url"], x["kind"], a["monthly_total"], x["deposit"], a["radius_m"], a["state"], x["contact"]["status"], "; ".join(a["reasons"] + a["gaps"])]
        writer.writerow(["'" + str(v) if isinstance(v, str) and v[:1] in {"=", "+", "-", "@", "\t", "\r"} else v for v in row])
    return out.getvalue()
