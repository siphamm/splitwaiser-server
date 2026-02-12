from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/me")
def get_me(request: Request):
    user = request.state.user
    if not user:
        return None
    return {"id": user.id, "name": user.name}
