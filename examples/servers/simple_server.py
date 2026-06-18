# @!documentation

# Same code works with Flask or FastAPI!
from axiompy.servers import ServerFactory, ServerSettings, ServerType

settings = ServerSettings(host="0.0.0.0", port=8000)
server = ServerFactory.create(ServerType.FASTAPI, settings)


@server.route("/users/{user_id}", methods=["GET"])
def get_user(user_id: int):
    return {"id": user_id, "name": f"User {user_id}"}


server.run()
