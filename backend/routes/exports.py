import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from ..database import get_db

router = APIRouter()


# ── TEI export ───────────────────────────────────────────────────────────────

@router.get("/tei/{ark_path:path}", response_class=Response)
async def export_tei(ark_path: str, db=Depends(get_db)):
    """Export annotations for a volume as TEI XML."""
    volume_ark = f"ark:/{ark_path}"
    rows = db.execute(
        "SELECT * FROM annotations WHERE volume_ark = ? ORDER BY created_at",
        (volume_ark,),
    ).fetchall()
    annotations = [dict(r) for r in rows]

    if not annotations:
        raise HTTPException(status_code=404, detail="No annotations found for this volume")

    tei = _build_tei(volume_ark, annotations)
    filename = f"toganoo-{ark_path.replace('/', '-')}-provenance.xml"
    return Response(
        content=tei,
        media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _build_tei(volume_ark: str, annotations: list) -> str:
    seal_elements, zone_elements, prov_elements = [], [], []

    for i, a in enumerate(annotations, 1):
        seal_id = f"mark-{i:03d}"
        zone_id = f"zone-{i:03d}"

        parts = []
        if a.get("shape"):
            parts.append(f'      <decoNote type="shape">{a["shape"]}</decoNote>')
        if a.get("ink_color"):
            parts.append(f'      <decoNote type="color">{a["ink_color"]}</decoNote>')
        if a.get("script_type"):
            parts.append(f'      <decoNote type="script">{a["script_type"]}</decoNote>')
        if a.get("condition"):
            parts.append(f'      <decoNote type="condition">{a["condition"]}</decoNote>')
        if a.get("transcription"):
            parts.append(f'      <ab xml:lang="ja">{a["transcription"]}</ab>')
        if a.get("transcription_rom"):
            parts.append(f'      <ab xml:lang="ja-Latn">{a["transcription_rom"]}</ab>')
        if a.get("location_on_object"):
            parts.append(f'      <note type="location">{a["location_on_object"]}</note>')
        if a.get("annotator_orcid"):
            parts.append(f'      <note type="annotator" resp="{a["annotator_orcid"]}">{a.get("annotator_name","")}</note>')

        seal_elements.append(
            f'    <seal xml:id="{seal_id}" type="{a.get("mark_type","")}" n="{i}" facs="#{zone_id}">\n'
            + "\n".join(parts)
            + "\n    </seal>"
        )

        zone_elements.append(
            f'    <surface xml:id="canvas-{i:03d}" source="{a.get("canvas_id","")}">\n'
            f'      <zone xml:id="{zone_id}" corresp="#{seal_id}"\n'
            f'            ulx="" uly="" lrx="" lry=""\n'
            f'            n="{a.get("region_xywh","")}" />\n'
            f'    </surface>'
        )

        prov_parts = []
        if a.get("owner_name"):
            ref = f' ref="{a["owner_authority_uri"]}"' if a.get("owner_authority_uri") else ""
            tag = "orgName" if a.get("owner_type") in {"temple","school","library","other-institution"} else "persName"
            prov_parts.append(f'<{tag}{ref} xml:lang="ja">{a["owner_name"]}</{tag}>')
        if a.get("place_name"):
            ref = f' ref="{a["place_authority_uri"]}"' if a.get("place_authority_uri") else ""
            prov_parts.append(f'<placeName{ref} xml:lang="ja">{a["place_name"]}</placeName>')

        if prov_parts:
            loc = a.get("location_on_object","")
            prov_elements.append(
                f'    <stamp xml:id="prov-{i:03d}" corresp="#{seal_id}" type="{a.get("mark_type","")}">\n'
                f'      {", ".join(prov_parts)}'
                + (f': {loc}.' if loc else "")
                + f'\n    </stamp>'
            )

    today = datetime.now().strftime("%Y-%m-%d")
    seals_block = "\n".join(seal_elements) if seal_elements else "    <!-- no annotations -->"
    zones_block = "\n".join(zone_elements) if zone_elements else "    <!-- no surfaces -->"
    prov_block = "\n".join(prov_elements) if prov_elements else "    <!-- no provenance entries -->"

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<?xml-model href="http://www.tei-c.org/release/xml/tei/custom/schema/relaxng/tei_all.rng"
            type="application/xml"
            schematypens="http://relaxng.org/ns/structure/1.0"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0">
  <teiHeader>
    <fileDesc>
      <titleStmt>
        <title>Toganoo Collection Provenance Data</title>
      </titleStmt>
      <publicationStmt>
        <publisher>UCLA Library</publisher>
        <pubPlace>Los Angeles</pubPlace>
        <date when="{today}"/>
        <availability status="restricted">
          <licence target="http://creativecommons.org/licenses/by-nc-sa/4.0/">
            This metadata is licensed under CC BY-NC-SA 4.0.
          </licence>
        </availability>
      </publicationStmt>
      <sourceDesc>
        <msDesc>
          <msIdentifier>
            <country>USA</country>
            <repository>UCLA Library</repository>
            <collection>Toganoo Collection</collection>
            <idno type="ARK">{volume_ark}</idno>
          </msIdentifier>
          <physDesc>
            <sealDesc>
{seals_block}
            </sealDesc>
          </physDesc>
          <history>
            <provenance>
{prov_block}
            </provenance>
          </history>
        </msDesc>
      </sourceDesc>
    </fileDesc>
    <facsimile>
{zones_block}
    </facsimile>
  </teiHeader>
  <text>
    <body><p/></body>
  </text>
</TEI>
"""


# ── Linked Art export ─────────────────────────────────────────────────────────

@router.get("/linked-art/{ark_path:path}")
async def export_linked_art(ark_path: str, db=Depends(get_db)):
    """Export annotations as a Linked Art JSON-LD document."""
    volume_ark = f"ark:/{ark_path}"
    rows = db.execute(
        "SELECT * FROM annotations WHERE volume_ark = ? ORDER BY created_at",
        (volume_ark,),
    ).fetchall()
    annotations = [dict(r) for r in rows]

    if not annotations:
        raise HTTPException(status_code=404, detail="No annotations found for this volume")

    base_uri = f"https://toganoo.library.ucla.edu/objects/{ark_path}"
    used_for = []

    for a in annotations:
        ownership_activity: dict = {
            "type": "Activity",
            "classified_as": [
                {
                    "id": "http://vocab.getty.edu/aat/300054277",
                    "_label": "ownership",
                    "type": "Type",
                }
            ],
        }
        if a.get("owner_name"):
            agent_type = "Group" if a.get("owner_type") in {"temple","school","library","other-institution"} else "Person"
            agent: dict = {
                "type": agent_type,
                "_label": a["owner_name"],
                "identified_by": [{"type": "Name", "content": a["owner_name"], "language": [{"id": "http://vocab.getty.edu/aat/300388412", "_label": "Japanese"}]}],
            }
            if a.get("owner_authority_uri"):
                agent["id"] = a["owner_authority_uri"]
            ownership_activity["carried_out_by"] = [agent]

        if a.get("place_name"):
            place: dict = {"type": "Place", "_label": a["place_name"]}
            if a.get("place_authority_uri"):
                place["id"] = a["place_authority_uri"]
            ownership_activity["took_place_at"] = [place]

        digital_ref: dict = {
            "type": "DigitalObject",
            "format": 'application/ld+json;profile="http://iiif.io/api/presentation/3/context.json"',
            "access_point": [{"id": f"{a.get('canvas_id','')}#xywh={a.get('region_xywh','')}"}],
        }

        mark: dict = {
            "type": "LinguisticObject",
            "_label": f"{a.get('mark_type','mark')}: {a.get('transcription','')}",
            "classified_as": [
                {
                    "id": "http://vocab.getty.edu/aat/300028619",
                    "_label": "collector's marks",
                    "type": "Type",
                }
            ],
            "digitally_shown_by": [digital_ref],
        }
        if a.get("transcription"):
            mark["content"] = a["transcription"]

        ownership_activity["referred_to_by"] = [mark]
        if a.get("annotator_orcid"):
            ownership_activity["attributed_by"] = [
                {
                    "type": "AttributeAssignment",
                    "carried_out_by": [{"id": a["annotator_orcid"], "type": "Person", "_label": a.get("annotator_name","")}],
                    "timespan": {"type": "TimeSpan", "begin_of_the_begin": a.get("created_at",""), "end_of_the_end": a.get("created_at","")},
                }
            ]

        used_for.append(ownership_activity)

    doc = {
        "@context": "https://linked.art/ns/v1/linked-art.json",
        "id": base_uri,
        "type": "HumanMadeObject",
        "_label": f"Toganoo Collection: {volume_ark}",
        "identified_by": [{"type": "Identifier", "content": volume_ark, "classified_as": [{"id": "http://vocab.getty.edu/aat/300404704", "_label": "ARK identifier"}]}],
        "used_for": used_for,
    }

    filename = f"toganoo-{ark_path.replace('/', '-')}-linked-art.json"
    return Response(
        content=json.dumps(doc, ensure_ascii=False, indent=2),
        media_type="application/ld+json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── W3C Web Annotation export ─────────────────────────────────────────────────

@router.get("/annotations/{ark_path:path}")
async def export_web_annotations(ark_path: str, db=Depends(get_db)):
    """Export annotations as a W3C Web Annotation collection."""
    volume_ark = f"ark:/{ark_path}"
    rows = db.execute(
        "SELECT * FROM annotations WHERE volume_ark = ? ORDER BY created_at",
        (volume_ark,),
    ).fetchall()
    annotations = [dict(r) for r in rows]

    items = []
    for a in annotations:
        body_text = f"{a.get('mark_type','mark')}"
        if a.get("transcription"):
            body_text += f": {a['transcription']}"
        if a.get("owner_name"):
            body_text += f" ({a['owner_name']})"

        item = {
            "@context": [
                "http://www.w3.org/ns/anno.jsonld",
                "https://iiif.io/api/presentation/3/context.json",
            ],
            "id": f"https://toganoo.library.ucla.edu/annotations/{a['id']}",
            "type": "Annotation",
            "motivation": "supplementing",
            "creator": {"id": a.get("annotator_orcid",""), "type": "Person", "name": a.get("annotator_name","")},
            "created": a.get("created_at",""),
            "modified": a.get("updated_at",""),
            "body": [
                {"type": "TextualBody", "value": body_text, "purpose": "describing", "language": "en"},
                {
                    "type": "Dataset",
                    "format": "application/json",
                    "purpose": "classifying",
                    "value": {
                        "markType": a.get("mark_type"),
                        "shape": a.get("shape"),
                        "color": a.get("ink_color"),
                        "scriptType": a.get("script_type"),
                        "condition": a.get("condition"),
                        "transcription": a.get("transcription"),
                        "transcriptionRomanized": a.get("transcription_rom"),
                        "owner": {
                            "name": a.get("owner_name"),
                            "type": a.get("owner_type"),
                            "authorityURI": a.get("owner_authority_uri"),
                        },
                        "place": {
                            "name": a.get("place_name"),
                            "authorityURI": a.get("place_authority_uri"),
                        },
                        "locationOnObject": a.get("location_on_object"),
                        "notes": a.get("notes"),
                    },
                },
            ],
            "target": {
                "source": a.get("canvas_id",""),
                "selector": {
                    "type": "FragmentSelector",
                    "conformsTo": "http://www.w3.org/TR/media-frags/",
                    "value": f"xywh={a.get('region_xywh','')}",
                },
            },
        }
        items.append(item)

    collection = {
        "@context": "http://www.w3.org/ns/anno.jsonld",
        "id": f"https://toganoo.library.ucla.edu/annotations/volume/{ark_path}",
        "type": "AnnotationCollection",
        "label": f"Provenance annotations for {volume_ark}",
        "total": len(items),
        "items": items,
    }

    filename = f"toganoo-{ark_path.replace('/', '-')}-annotations.json"
    return Response(
        content=json.dumps(collection, ensure_ascii=False, indent=2),
        media_type="application/ld+json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
