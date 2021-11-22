import pytest
from test_helpers import make_request_from_file
import json

# Test GET / basic functionality
def test_root_get_basic():
    status, headers, body = make_request_from_file("http_files/root_get_basic.http")
    assert status==200
    with open("../app/perm_contents/welcome.html","r") as f:
        expected_body = f.read()
    assert body.decode()==expected_body

# Test GET / for idempotence - for 3 GET requests / should return 200 with the same resource
def test_root_get_idempotence():
    status_0, headers_0, body_0 = make_request_from_file("http_files/root_get_basic.http")
    status_1, headers_1, body_1 = make_request_from_file("http_files/root_get_basic.http")
    status_2, headers_2, body_2 = make_request_from_file("http_files/root_get_basic.http")
    assert status_0==status_1
    assert status_1==status_2
    assert body_0==body_1
    assert body_1==body_2

# Test POST /contributors basic functionality
def test_contributors_post_basic():
    try:
        status, headers, body = make_request_from_file("http_files/contributors_post_1.http")
        assert status == 200
        body = json.loads(body)
        assert body["success"] == True
        assert body["new_user_created"] == True
        assert body["path"] == "/contributors/aaaaa"
        assert len(body)==3
        status, headers, body = make_request_from_file("http_files/contributors_get_basic.http")
        assert status==200
        body = json.loads(body)
        assert body[0]["username"]=="aaaaa"
        assert body[0]["name"]=="bbbbb"
        assert body[0]["bio"]=="ccccc"
        make_request_from_file("http_files/contributors_username_delete_1.http")
    except Exception as e:
        print(e)
        make_request_from_file("http_files/contributors_username_delete_1.http")
        assert False

# Test POST /contributors for input validation
def test_contributors_post_input_validation():
    files = ["http_files/contributors_post_malformed_{}.http".format(i) for i in range(1,8)]
    for i in files:
        status, _1, _2 = make_request_from_file(i)
        assert status == 422

# Test POST /contributors for idempotence, as measured by constant success and path returned,
# and is_new_user switched to False after initial creation
def test_contributors_post_idempotence():
    try:
        _1, _2, body1 = make_request_from_file("http_files/contributors_post_1.http")
        _1, _2, body2 = make_request_from_file("http_files/contributors_post_1.http")
        _1, _2, body3 = make_request_from_file("http_files/contributors_post_1.http")
        bodies = [body1,body2,body3]
        bodies = [json.loads(i) for i in bodies]
        for i in bodies:
            assert i["success"] == True
            assert i["path"] == "/contributors/aaaaa"
        assert bodies[0]["new_user_created"] == True
        assert bodies[1]["new_user_created"] == False
        assert bodies[2]["new_user_created"] == False
        make_request_from_file("http_files/contributors_username_delete_1.http")
    except Exception as e:
        print(e)
        make_request_from_file("http_files/contributors_username_delete_1.http")
        assert False

# Test GET /contributors/[username] for basic func
def test_contributors_username_get_basic():
    try:
        make_request_from_file("http_files/contributors_post_1.http")
        status, _1, body = make_request_from_file("http_files/contributors_username_get_1.http")
        body = json.loads(body)
        assert body["name"]=="bbbbb"
        assert body["bio"]=="ccccc"
        make_request_from_file("http_files/contributors_username_delete_1.http")
    except Exception as e:
        print(e)
        make_request_from_file("http_files/contributors_username_delete_1.http")
        assert False

# Test GET /contributors/[username] for if user doesnt exist
def test_contributors_username_get_error():
    status, _1, _2 = make_request_from_file("http_files/contributors_username_get_1.http")
    assert status == 404

# Test GET /contributors/[username] for idempotence through repeating request for when user exists,
# and for when user doesn't
def test_contributors_username_get_idempotence():
    status1, _1, body1 = make_request_from_file("http_files/contributors_username_get_1.http")
    status2, _1, body2 = make_request_from_file("http_files/contributors_username_get_1.http")

    assert status1==404
    assert status1==status2
    assert body1==body2
    try:
        make_request_from_file("http_files/contributors_post_1.http")
        status1, _1, body1 = make_request_from_file("http_files/contributors_username_get_1.http")
        status2, _1, body2 = make_request_from_file("http_files/contributors_username_get_1.http")
        assert status1==200
        assert status1==status2
        assert body1==body2
        make_request_from_file("http_files/contributors_username_delete_1.http")
    except Exception as e:
        print(e)
        make_request_from_file("http_files/contributors_username_delete_1.http")
        assert False

# Test PUT /contributors/[username] for basic functionality
def test_contributors_username_put_basic():
    try:
        make_request_from_file("http_files/contributors_post_1.http")
        status, _, body = make_request_from_file("http_files/contributors_username_put_1.http")
        assert status==200
        body = json.loads(body)
        assert body["success"]==True
        make_request_from_file("http_files/contributors_username_delete_1.http")
    except Exception as e:
        print(e)
        make_request_from_file("http_files/contributors_username_delete_1.http")
        assert False

# Test PUT /contributors/[username] for 404 error handling
def test_contributors_username_put_not_found_error():
    try:
        status, _, body = make_request_from_file("http_files/contributors_username_put_1.http")
        assert status==404
    except Exception as e:
        print(e)
        make_request_from_file("http_files/contributors_username_delete_1.http")
        assert False

# Test PUT /contributors/[username] for input validation
def test_contributors_username_put_validation_error():
    try:
        make_request_from_file("http_files/contributors_post_1.http")
        files = ["http_files/contributors_username_put_1_malformed_{}.http".format(i) for i in range(1,4)]
        for i in files:
            status, _, body = make_request_from_file(i)
            assert status==422
        make_request_from_file("http_files/contributors_username_delete_1.http")
    except Exception as e:
        print(e)
        make_request_from_file("http_files/contributors_username_delete_1.http")
        assert False

# Test PUT /contributors/[username] for idempotence in all 3 cases (no user found, invalid update, multiple updates)
    try:
        status1, _, body1 = make_request_from_file("http_files/contributors_username_put_1.http")
        status2, _, body2 = make_request_from_file("http_files/contributors_username_put_1.http")
        assert status1 == 404
        assert status1==status2
        assert body1==body2

        make_request_from_file("http_files/contributors_post_1.http")
        status1, _, body1 = make_request_from_file("http_files/contributors_username_put_1_malformed_1.http")
        status2, _, body2 = make_request_from_file("http_files/contributors_username_put_1_malformed_1.http")
        assert status1==422
        assert status1==status2
        assert body1==body2

        status1, _, body1 = make_request_from_file("http_files/contributors_username_put_1.http")
        status2, _, body2 = make_request_from_file("http_files/contributors_username_put_1.http")
        assert status1==200
        assert status1==status2
        assert body1==body2
        make_request_from_file("http_files/contributors_username_delete_1.http")
    except Exception as e:
        print(e)
        make_request_from_file("http_files/contributors_username_delete_1.http")
        assert False

# Test GET /contributors for basic functionality, without query params
def test_get_contributors_basic():
    indexes = list(range(1,6))
    try:
        for i in indexes:
            make_request_from_file("http_files/contributors_post_{}.http".format(i))
        status, _, body = make_request_from_file("http_files/contributors_get_basic.http".format(i))
        assert status==200
        body = json.loads(body)
        expected_body = [
            {
                "username": "aaaaa",
                "name": "bbbbb",
                "bio": "ccccc"
            },
            {
                "username": "aaaaa1",
                "name": "bbbbb1",
                "bio": "ccccc1"
            },
            {
                "username": "bbbbb",
                "name": "ccccc",
                "bio": "aaaaa"
            },
            {
                "username": "ddddd",
                "name": "aaaaa",
                "bio": ""
            },
            {
                "username": "sssss",
                "name": "11111",
                "bio": ""
            }
        ]

        for i in range(len(body)):
            for j in range(len(expected_body)):
                if body[i]["username"]==expected_body[j]["username"] and body[i]["name"]==expected_body[j]["name"] and body[i]["bio"]==expected_body[j]["bio"]:
                    expected_body.pop(j)
                    break
        assert len(expected_body)==0
        for i in indexes: make_request_from_file("http_files/contributors_username_delete_{}.http".format(i))
    except Exception as e:
        print(e)
        for i in indexes: make_request_from_file("http_files/contributors_username_delete_{}.http".format(i))
        assert False

# Test GET /contributors with invalid query params
def test_get_contributors_sortby_error():
    for i in range(1,5):
        status, _1, _2 = make_request_from_file("http_files/contributors_get_malformed_{}.http".format(i))
        assert status==422

# Test GET /contributors with only sortBy query params
def test_get_contributors_sortby():
    try:
        make_request_from_file("http_files/contributors_post_1.http")
        make_request_from_file("http_files/contributors_post_4.http")
        expected_body = [
            {
                "username": "aaaaa",
                "name": "bbbbb",
                "bio": "ccccc"
            },{
                "username": "ddddd",
                "name": "aaaaa",
                "bio": ""
            }
        ]
        status, _2, body = make_request_from_file("http_files/contributors_get_sortby_1.http")
        assert status==200
        expected_body = sorted(expected_body,key=lambda x:x["username"])
        body = json.loads(body)
        for i in range(len(body)):
            assert body[i]["username"]==expected_body[i]["username"]
            assert body[i]["name"]==expected_body[i]["name"]
            assert body[i]["bio"]==expected_body[i]["bio"]
        status, _2, body = make_request_from_file("http_files/contributors_get_sortby_2.http")
        assert status==200
        expected_body = sorted(expected_body,key=lambda x:x["name"])
        body = json.loads(body)
        for i in range(len(body)):
            assert body[i]["username"]==expected_body[i]["username"]
            assert body[i]["name"]==expected_body[i]["name"]
            assert body[i]["bio"]==expected_body[i]["bio"]
        make_request_from_file("http_files/contributors_username_delete_1.http")
        make_request_from_file("http_files/contributors_username_delete_4.http")
    except Exception as e:
        print(e)
        make_request_from_file("http_files/contributors_username_delete_1.http")
        make_request_from_file("http_files/contributors_username_delete_4.http")
        assert False
    
# Test GET /contributors with only count query params
def test_get_contributors_count():
    indexes = list(range(1,6))
    try:
        for i in indexes:
            make_request_from_file("http_files/contributors_post_{}.http".format(i))
        status, _, body = make_request_from_file("http_files/contributors_get_count_1.http")
        assert status==200
        body = json.loads(body)
        assert len(body)==3
        for i in indexes: make_request_from_file("http_files/contributors_username_delete_{}.http".format(i))
    except Exception as e:
        print(e)
        for i in indexes: make_request_from_file("http_files/contributors_username_delete_{}.http".format(i))
        assert False

# Test GET /contributors with only offset query params
def test_get_contributors_offset():
    indexes = list(range(1,6))
    try:
        for i in indexes:
            make_request_from_file("http_files/contributors_post_{}.http".format(i))
        status, _, body = make_request_from_file("http_files/contributors_get_offset_1.http")
        assert status==200
        body = json.loads(body)
        assert len(body)==2
        for i in indexes: make_request_from_file("http_files/contributors_username_delete_{}.http".format(i))
    except Exception as e:
        print(e)
        for i in indexes: make_request_from_file("http_files/contributors_username_delete_{}.http".format(i))
        assert False

# Test GET /contributors with combined query params
def test_get_contributors_combined_query():
    indexes = list(range(1,6))
    try:
        for i in indexes:
            make_request_from_file("http_files/contributors_post_{}.http".format(i))
        status, _, body = make_request_from_file("http_files/contributors_get_combined_1.http")
        assert status==200
        body = json.loads(body)
        assert len(body)==1
        status, _, body = make_request_from_file("http_files/contributors_get_combined_2.http")
        assert status==200
        body = json.loads(body)
        assert len(body)==2
        for i in indexes: make_request_from_file("http_files/contributors_username_delete_{}.http".format(i))
    except Exception as e:
        print(e)
        for i in indexes: make_request_from_file("http_files/contributors_username_delete_{}.http".format(i))
        assert False
        
