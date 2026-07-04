from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from typing import Dict

router = APIRouter(tags=["Authentication"])

# In a real app, this would use proper hashing and a database
MOCK_USERS = {
    "admin@supplymind.ai": "admin"
}

@router.post("/auth/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()) -> Dict[str, str]:
    """
    Mock JWT authentication endpoint for Phase 5 frontend integration.
    """
    # Check mock credentials
    if form_data.username not in MOCK_USERS or MOCK_USERS[form_data.username] != form_data.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Return a real signed JWT token
    from api.middleware.auth import create_jwt_token
    real_jwt = create_jwt_token(user_id=form_data.username, role=MOCK_USERS[form_data.username])
    
    return {
        "access_token": real_jwt,
        "token_type": "bearer"
    }
