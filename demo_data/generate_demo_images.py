"""Generate deterministic synthetic SVG fixtures for local UI demonstrations.

The output is deliberately illustrative and does not contain biometric data or
perform facial recognition. It mirrors the rows in manifest.csv.
"""

from pathlib import Path

OUTPUT_DIR = Path(__file__).resolve().parent / "images"
PALETTES = [
    ("#d7b08a", "#203a56", "#3c6082"),
    ("#8f5f45", "#342b36", "#62516d"),
    ("#5f3b2e", "#263b38", "#41645f"),
    ("#c8936e", "#3d3f54", "#666982"),
    ("#a46d4d", "#303c52", "#526a8a"),
    ("#704634", "#4b3542", "#76586a"),
]


def build_svg(index: int) -> str:
    skin, hair, clothing = PALETTES[(index - 1) % len(PALETTES)]
    hair_variant = 38 + (index % 4) * 3
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="320" height="320" viewBox="0 0 320 320" role="img" aria-label="Synthetic demo portrait {index:03d}">
  <rect width="320" height="320" fill="#102238"/>
  <rect x="18" y="18" width="284" height="284" rx="4" fill="#172d45" stroke="#38546f"/>
  <circle cx="160" cy="132" r="70" fill="{skin}"/>
  <path d="M90 131c0-58 29-88 70-88s70 30 70 88c-22-{hair_variant} 20-{hair_variant} 0-36-18-65-18z" fill="{hair}"/>
  <circle cx="134" cy="135" r="5" fill="#17202b"/>
  <circle cx="186" cy="135" r="5" fill="#17202b"/>
  <path d="M146 169c10 7 18 7 28 0" fill="none" stroke="#653f37" stroke-width="4" stroke-linecap="round"/>
  <path d="M74 302c8-72 44-105 86-105s78 33 86 105" fill="{clothing}"/>
  <rect x="30" y="274" width="76" height="18" fill="#102238"/>
  <text x="38" y="287" fill="#91aac2" font-family="monospace" font-size="10">FB-{index:03d}</text>
</svg>
"""


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for index in range(1, 37):
        (OUTPUT_DIR / f"synthetic_face_{index:03d}.svg").write_text(
            build_svg(index), encoding="utf-8"
        )


if __name__ == "__main__":
    main()
