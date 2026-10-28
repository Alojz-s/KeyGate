ARTICLES_READ = "articles.read"
ARTICLES_WRITE = "articles.write"
USERS_MANAGE = "users.manage"
SETTINGS_MANAGE = "settings.manage"

# Jedyne źródło macierzy uprawnień - korzysta z niej seed;
# docs/macierz-uprawnien.md jest jej kopią i trzeba ją aktualizować razem z tym słownikiem.
ROLE_PERMISSION_MATRIX: dict[str, list[str]] = {
    "Administrator": [ARTICLES_READ, USERS_MANAGE, SETTINGS_MANAGE],
    "Audytor": [ARTICLES_READ],
    "Redaktor": [ARTICLES_READ, ARTICLES_WRITE],
    "Czytelnik": [ARTICLES_READ],
}
