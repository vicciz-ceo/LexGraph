"""Router package. Empty on purpose (R2): the bare app factory registers no
routes. Each Developer track adds its own router module here and includes
it in `app.main.create_app()`. Track ownership (see sprint contract):

- B1  -> assertions.py   (assertions CRUD, evidence, revisions)
- B2  -> ratings.py      (rating PUT/GET/DELETE, summary)
- B3  -> comments.py     (comments CRUD)
- B4  -> review.py       (accept/reject/dispute/request-revision/supersede)
- B5  -> extends assertions.py (search/sort query params, duplicate check)
- B6  -> graph.py, notifications.py
"""
