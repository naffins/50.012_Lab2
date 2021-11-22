from fastapi import FastAPI, Response, File, Form, Depends
from pydantic import BaseModel, Field
import redis
import threading
import enum
import random
import hashlib
import json
import time

from image_utils import check_png, apply_shitpost

# JSON template model for adding new contributors
class Contributor(BaseModel):
    username: str = Field(...,min_length=3,max_length=20,regex="^[a-zA-Z0-9_]*$")
    name: str = Field(...,min_length=3,max_length=30,regex="^[a-zA-Z0-9 ]*$")
    bio: str

# JSON template model for modifying existing contributors
class Contributor_Update(BaseModel):
    name: str = Field(...,min_length=3,max_length=30,regex="^[a-zA-Z0-9 ]*$")
    bio: str

# Enum for sorting options for contributors list
class SortBy_Options(str,enum.Enum):
    username = "username"
    name = "name"

# Initialize server
app = FastAPI()

# Semaphores for contributors/image systems
contributor_semaphore = threading.Semaphore()
image_semaphore = threading.Semaphore()

# Constant strings
USERS_KEY = "contributors"
IMG_KEY_PREFIX = "img_"
USER_NOT_FOUND_ERR = "CONTRIBUTOR_NOT_FOUND"
UNAUTHORIZED_ERR = "MUST_BE_REGISTERED_CONTRIBUTOR"
IMG_NOT_FOUND_ERR = "IMAGE_NOT_FOUND"
WELCOME_HTML = "./perm_contents/welcome.html"

# Get Redis client (connection taken from internal pool, host at "redis")
def get_redis_client():
    return redis.Redis(host="redis")

# Welcome page - tested
@app.get("/")
def get_root_help_page():
    
    # Open prewritten HTML page and send to client
    with open(WELCOME_HTML,"r") as f:
        welcome_message = f.read()
    return Response(content=welcome_message,media_type="text/html")

# Add or update user - tested
@app.post("/contributors")
def add_user(contributor: Contributor, redis_client: redis.Redis = Depends(get_redis_client)):

    # Access contributor system semaphore
    global contributor_semaphore

    # While acquiring semaphore, set user info, checking if new user is created
    # name and bio strings are joined by ";"
    contributor_semaphore.acquire()
    is_new_user = redis_client.hset(USERS_KEY,key=contributor.username,value="{};{}".format(contributor.name,contributor.bio))
    contributor_semaphore.release()

    # Return add user result
    return {"success": True, "new_user_created": is_new_user==1, "path": "/contributors/{}".format(contributor.username)}

# View specific user details - tested
@app.get("/contributors/{username}")
def get_user(username: str, response: Response, redis_client: redis.Redis = Depends(get_redis_client)):

    # Get data from hash pair containing dictionary in Redis DB
    user_data =  redis_client.hget(USERS_KEY,username)

    # If None was returned, then key doesn't exist in nested dict
    # Otherwise parse result and return
    if not user_data==None:
        user_data = user_data.decode()
        index = user_data.index(";")
        return {"name": user_data[:index], "bio": user_data[index+1:]}
    else:
        response.status_code = 404
        return {"error": USER_NOT_FOUND_ERR}        

# Strictly update user - tested
@app.put("/contributors/{username}")
def update_user(username: str, contributor_update: Contributor_Update, response: Response, redis_client: redis.Redis = Depends(get_redis_client)):
    
    # Access contributor system semaphore
    global contributor_semaphore

    # While locking, check if user exists - if it doesn't return an error, but if it does then perform update
    contributor_semaphore.acquire()
    return_data = {"success": True}
    if redis_client.hexists(USERS_KEY,username):
        redis_client.hset(USERS_KEY,key=username,value="{};{}".format(contributor_update.name,contributor_update.bio))
    else:
        return_data = {"success": False, "error": USER_NOT_FOUND_ERR}
        response.status_code = 404
    contributor_semaphore.release()
    return return_data

# Delete user
@app.delete("/contributors/{username}")
def delete_user(username:str, response: Response, redis_client: redis.Redis = Depends(get_redis_client)):

    # Acquire contributor system semaphore and delete, checking if any deletion occurred
    global contributor_semaphore
    contributor_semaphore.acquire()
    user_exists = redis_client.hdel(USERS_KEY,username)
    contributor_semaphore.release()

    # If no deletion occurred return an error
    if user_exists == 1:
        return {"success": True}
    else:
        response.status_code = 404
        return {"success": False, "error": USER_NOT_FOUND_ERR}
        

# Get list of all users, with query parameters - tested
@app.get("/contributors")
def get_user_list(sortBy: SortBy_Options = None, count: int = None, offset: int = 0, redis_client: redis.Redis = Depends(get_redis_client)):
    
    # Get list of all users and parse
    retrieved_data = redis_client.hgetall(USERS_KEY)
    retrieved_data = {i: retrieved_data[i].decode().split(";") for i in retrieved_data}
    retrieved_data = [{"username": i, "name": retrieved_data[i][0], "bio": ";".join(retrieved_data[i][1:])} for i in retrieved_data]

    # Perform sorting if needed
    if not sortBy==None:
        retrieved_data = sorted(retrieved_data,key=lambda x: x[sortBy])
    
    # Process offset and count
    if not count==None:
        retrieved_data = retrieved_data[offset:offset+count]
    else:
        retrieved_data = retrieved_data[offset:]
    
    return retrieved_data

# Post new image - method cannot be used for update due to generation of new identifiers
@app.post("/images")
def post_image(response: Response, file: bytes = File(...), username: str = Form(...), redis_client: redis.Redis = Depends(get_redis_client)):
    
    # Check if username exists, if not reject
    if not redis_client.hexists(USERS_KEY,username):
        response.status_code = 401
        return {"error": UNAUTHORIZED_ERR}

    # Verify that the file is a PNG file
    is_png, error_msg = check_png(file)
    if not is_png:
        response.status_code = 400
        return {"error": error_msg}
    
    # Create identifier that makes use of RNG and current time
    identifier = hashlib.md5(file).digest()+str(time.time()).encode()+str(random.random()).encode()
    identifier = hashlib.md5(identifier).hexdigest()

    # Acquire image system semaphore and upload to DB
    global image_semaphore
    image_semaphore.acquire()
    redis_client.set("{}{}".format(IMG_KEY_PREFIX,identifier),file)
    image_semaphore.release()

    return {"success": True, "path": "/images/{}".format(identifier)}

# Strictly update image - works similarly to POST except that no new identifier is generated
@app.put("/images/{identifier}")
def update_image(response: Response, identifier: str, file: bytes = File(...), username: str = Form(...), redis_client: redis.Redis = Depends(get_redis_client)):
    if not redis_client.hexists(USERS_KEY,username):
        response.status_code = 401
        return {"error": UNAUTHORIZED_ERR}
    is_png, error_msg = check_png(file)
    if not is_png:
        response.status_code = 404
        return {"error": error_msg}
    global image_semaphore
    image_semaphore.acquire()
    return_val = None
    if redis_client.exists("{}{}".format(IMG_KEY_PREFIX,identifier)):
        oldfile = redis_client.getset("{}{}".format(IMG_KEY_PREFIX,identifier),file)
        return_val = {"success": True, "image_changed": not oldfile==file}
    else:
        response.status_code = 404
        return_val = {"error": IMG_NOT_FOUND_ERR}
    image_semaphore.release()
    return return_val

# Delete image
@app.delete("/images/{identifier}")
def delete_image(response: Response, identifier: str, redis_client: redis.Redis = Depends(get_redis_client)):
    
    # Acquire semaphore and attempt delete
    global image_semaphore
    image_semaphore.acquire()
    exists = redis_client.delete("{}{}".format(IMG_KEY_PREFIX,identifier))
    image_semaphore.release()

    # Check deletion result for whether file existed
    if exists==1:
        return {"success": True}
    else:
        response.status_code = 404
        return {"error": IMG_NOT_FOUND_ERR}

# Get image
@app.get("/images/{identifier}")
def get_image(identifier: str, redis_client: redis.Redis = Depends(get_redis_client)):
    
    # Acquire semaphore and get and modify image, then push image back to DB
    global image_semaphore
    image_semaphore.acquire()
    img = redis_client.get("{}{}".format(IMG_KEY_PREFIX,identifier))
    if img==None:
        image_semaphore.release()
        return Response(content=json.dumps({"error": IMG_NOT_FOUND_ERR}),media_type="application/json",status_code=404)
    
    new_img = apply_shitpost(img)
    redis_client.set("{}{}".format(IMG_KEY_PREFIX,identifier),new_img)
    image_semaphore.release()

    return Response(content=new_img,media_type="image/png")