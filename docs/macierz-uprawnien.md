# Macierz uprawnień ról

KeyGate stosuje kontrolę dostępu opartą na rolach (RBAC): uprawnienia są przypisane rolom, a role
użytkownikom (jedna rola na użytkownika). Każda rola ma tylko uprawnienia niezbędne do swojej
pracy (zasada najmniejszych uprawnień) – dlatego Administrator zarządza kontami i ustawieniami,
ale nie redaguje artykułów.

| Uprawnienie       | Administrator | Audytor | Redaktor | Czytelnik |
|-------------------|:-------------:|:-------:|:--------:|:---------:|
| `articles.read`   | tak           | tak     | tak      | tak       |
| `articles.write`  | nie           | nie     | tak      | nie       |
| `users.manage`    | tak           | nie     | nie      | nie       |
| `settings.manage` | tak           | nie     | nie      | nie       |

W module 1 Audytor ma dostęp tylko do odczytu, tak jak Czytelnik; uprawnienie do przeglądania
dziennika zdarzeń dojdzie w module 2.

## Endpointy chronione

| Endpoint                                     | Wymagane uprawnienie |
|----------------------------------------------|----------------------|
| `GET /api/articles`                          | `articles.read`      |
| `POST /api/articles`                         | `articles.write`     |
| `GET /api/admin/roles`                       | `users.manage`       |
| `GET`, `POST /api/admin/users`               | `users.manage`       |
| `PATCH`, `DELETE /api/admin/users/{id}`      | `users.manage`       |
| `POST /api/admin/users/{id}/block`           | `users.manage`       |
| `POST /api/admin/users/{id}/unblock`         | `users.manage`       |
| `POST /api/admin/users/{id}/reset-password`  | `users.manage`       |
| `GET`, `PUT /api/admin/settings`             | `settings.manage`    |

Brak uprawnienia: `403 {"detail": "Brak uprawnień do wykonania tej operacji", "code": "forbidden"}`.
Uprawnienia sprawdza wyłącznie backend; ukrywanie linków w interfejsie to tylko wygoda.

Źródłem macierzy jest `ROLE_PERMISSION_MATRIX` w `backend/app/core/permissions.py` (z niego korzysta
`scripts/seed.py`). Tabela powyżej jest jego kopią; siatkę rola × endpoint sprawdzają
`backend/tests/test_permissions.py`, `test_admin_users.py` i `test_admin_settings.py`.
