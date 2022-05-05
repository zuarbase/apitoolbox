from fastapi import FastAPI, Request

from apitoolbox import crud, db_registry
from apitoolbox.middleware import SessionMiddleware
from apitoolbox.models import BASE, Session, User

DATABASE_URL = "sqlite:///sqlite.db?check_same_thread=False"


# Define our model
class MyUser(User):
    pass


# Instantiate the application
app = FastAPI()
app.add_middleware(SessionMiddleware, bind=DATABASE_URL)

# Create all tables
bind = db_registry.get_or_create(DATABASE_URL)
BASE.metadata.create_all(bind=bind)

# Load some data
# session = Session()
# for name in ["alice", "bob", "charlie", "david"]:
#     user = MyUser.get_by_username(session, name)
#     if user is None:
#         user = MyUser(username=name)
#         session.add(user)
# session.commit()

# Add an endpoint
@app.get("/users")
async def list_users(request: Request):
    return await crud.list_instances(MyUser, request.state.session)
