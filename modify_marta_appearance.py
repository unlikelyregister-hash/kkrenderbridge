"""Modify MartaCard.png to match Marta Lorente's visual appearance.

Target appearance from the reference card:
  - Hair: blonde (kind 27, wavy side-part), blonde base + light blonde highlights
  - Eyes: hazel (type 08), green-brown hazel color
  - Skin: tanned (type 04), darker warm skin tone
  - Makeup: eyeliner 03, lip 02 (glossy), blush 01
  - Body: athletic, warm skin
  - Clothes: white crochet halter top + white sarong

Since we don't know exact asset IDs for Marta's hair/clothes, we modify
the colors and sliders on the existing Scarlet Chika base to get close.
"""
from pathlib import Path
from kkloader import KoikatuCharaData

CARD = Path("MartaCard.png")
OUT = Path("MartaCard_v2.png")


def modify_card(src: Path, dst: Path):
    chara = KoikatuCharaData.load(str(src))

    # ── Skin: tanned warm tone ──────────────────────────────────────────
    body = chara["Custom"]["body"]
    # Tanned skin: main color warmer/darker, sunburn for beach look
    body["skinMainColor"] = [1.0, 0.78, 0.62, 1.0]    # warm tan
    body["skinSubColor"] = [1.0, 0.55, 0.40, 1.0]     # warm undertone
    body["sunburnColor"] = [1.0, 0.95, 0.70, 0.45]    # light sunburn
    body["skinGlossPower"] = 0.35
    # Nail color - light nude
    body["nailColor"] = [0.95, 0.85, 0.75, 1.0]
    body["nailGlossPower"] = 0.6
    # Nip colors - tan
    body["nipColor"] = [1.0, 0.72, 0.62, 1.0]
    body["nipGlossPower"] = 0.5

    # ── Face: hazel eyes, blonde hair, makeup ───────────────────────────
    face = chara["Custom"]["face"]

    # Pupil color: hazel (green-brown mix)
    # baseColor = hazel green-brown, subColor = darker limbal ring
    if "pupil" in face and isinstance(face["pupil"], list) and len(face["pupil"]) >= 2:
        face["pupil"][0]["baseColor"] = [0.72, 0.65, 0.35, 1.0]   # hazel green-brown
        face["pupil"][0]["subColor"] = [0.55, 0.38, 0.25, 1.0]   # dark brown limbal
        # Apply same to second eye if present
        if len(face["pupil"]) >= 2:
            face["pupil"][1]["baseColor"] = [0.72, 0.65, 0.35, 1.0]
            face["pupil"][1]["subColor"] = [0.55, 0.38, 0.25, 1.0]

    # Eyeliner color: dark brown
    face["eyelineColor"] = [0.35, 0.20, 0.15, 1.0]

    # Lip color: glossy nude-pink
    face["lipLineColor"] = [0.90, 0.55, 0.50, 1.0]
    face["lipGlossPower"] = 0.7

    # Blush color: warm peach
    face["cheekGlossPower"] = 0.15  # minimal but present

    # ── Hair: blonde ─────────────────────────────────────────────────────
    hair = chara["Custom"]["hair"]
    if "parts" in hair and isinstance(hair["parts"], list):
        for part in hair["parts"]:
            if isinstance(part, dict):
                # Blonde base with honey highlights
                part["baseColor"] = [0.75, 0.65, 0.25, 1.0]     # medium blonde
                part["startColor"] = [0.85, 0.75, 0.40, 1.0]    # light blonde root
                part["endColor"] = [0.92, 0.85, 0.55, 1.0]      # honey blonde tips
                # Accent colors for blonde
                if "acsColor" in part and isinstance(part["acsColor"], list):
                    for ac in part["acsColor"]:
                        if isinstance(ac, list) and len(ac) >= 4 and ac[0] > 0:
                            ac[0] = 0.90
                            ac[1] = 0.80
                            ac[2] = 0.50
                            ac[3] = 1.0

    # ── Body shape: athletic ─────────────────────────────────────────────
    # Adjust bust weight for athletic look
    body["bustWeight"] = 0.35
    body["bustSoftness"] = 0.5
    body["areolaSize"] = 0.5
    body["detailPower"] = 0.6

    # ── Save ─────────────────────────────────────────────────────────────
    dst.parent.mkdir(parents=True, exist_ok=True)
    chara.save(str(dst))
    print(f"Saved: {dst} ({dst.stat().st_size} bytes)")

    # Verify key changes
    v = KoikatuCharaData.load(str(dst))
    bp = v["Custom"]["body"]
    fp = v["Custom"]["face"]
    hp = v["Custom"]["hair"]

    print(f"\nVerification:")
    print(f"  skinMainColor: {bp['skinMainColor']}")
    print(f"  pupil[0].baseColor: {fp['pupil'][0]['baseColor'] if 'pupil' in fp and len(fp['pupil']) > 0 else 'N/A'}")
    print(f"  hair[0].baseColor: {hp['parts'][0]['baseColor'] if 'parts' in hp and len(hp['parts']) > 0 else 'N/A'}")
    print(f"  hair[0].endColor: {hp['parts'][0]['endColor'] if 'parts' in hp and len(hp['parts']) > 0 else 'N/A'}")
    print(f"  bustWeight: {bp['bustWeight']}")
    print(f"  lipGlossPower: {fp['lipGlossPower']}")
    print(f"\n[DONE] MartaCard_v2.png ready for render")


if __name__ == "__main__":
    modify_card(CARD, OUT)
