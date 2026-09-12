"""Ingesta de Google Play reviews (Capa de confirmación). Sin ToS: librería oficial."""
from google_play_scraper import Sort, reviews_all

from schema import Item, hash_author

APP_ID = "com.win.miwin_app"


def fetch_reviews(app_id=APP_ID, lang="es", country="pe"):
    raw = reviews_all(
        app_id,
        sleep_milliseconds=200,
        lang=lang,
        country=country,
        sort=Sort.NEWEST,
    )
    items = []
    for r in raw:
        items.append(
            Item(
                fuente="google_play",
                texto=r.get("content", ""),
                fecha=r["at"].isoformat() if r.get("at") else "",
                url=f"https://play.google.com/store/apps/details?id={app_id}&reviewId={r.get('reviewId')}",
                autor_hash=hash_author(r.get("userName", "")),
                rating=r.get("score"),
                engagement={"thumbsUp": r.get("thumbsUpCount", 0)},
            ).to_dict()
        )
    return items


if __name__ == "__main__":
    items = fetch_reviews()
    print(f"{len(items)} reseñas recolectadas")
    for it in items[:5]:
        print(it["fecha"], it["rating"], "-", it["texto"][:80])
