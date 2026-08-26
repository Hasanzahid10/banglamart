CATEGORY_LIST_CACHE_KEY = "banglamart:category:list"

CATEGORY_CACHE_TTL = 60 * 15  # 15 minutes


def category_detail_cache_key(slug):
    return f"banglamart:category:detail:{slug}"