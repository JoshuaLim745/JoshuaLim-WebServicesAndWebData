import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from databaseModel import User, get_db

# 1. Configuration Constants
SECRET_KEY = "your-super-secret-key-here"  # In production, use an environment variable
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# 2. OAuth2 Scheme definition
# This tells FastAPI that the token is obtained from the "/users/login" endpoint
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="users/login")

# 3. Password Hashing Utilities (Centralized from your CRUD files)
def hash_password(password: str) -> str:
    """Encodes, truncates, and hashes a password string."""
    pwd_bytes = password.encode('utf-8')[:72]
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Checks a plain text password against a stored hash."""
    try:
        pwd_bytes = plain_password.encode('utf-8')[:72]
        hash_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(pwd_bytes, hash_bytes)
    except Exception:
        return False

# 4. JWT Token Creation
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Generates a signed JSON Web Token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# 5. The "get_current_user" Dependency
async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """
    Decodes the token, validates it, and returns the User object from the DB.
    Inject this into any route that needs authentication.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Decode the JWT
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # Fetch user from your databaseModel.User table
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    return user