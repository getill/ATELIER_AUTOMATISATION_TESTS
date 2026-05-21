def test_artworks_list_status(client):
    """
    Verifies that calling GET /artworks returns a 200 OK status code 
    and the response headers indicate a JSON payload.
    """
    res = client.get("/artworks")
    if res["status_code"] is None:
        raise AssertionError(f"Network error: {res['error']}")
    assert res["status_code"] == 200, f"Expected status 200, got {res['status_code']}"
    
    content_type = res["headers"].get("Content-Type", "")
    assert "application/json" in content_type, f"Expected JSON content-type, got '{content_type}'"


def test_artworks_list_structure(client):
    """
    Verifies that the /artworks endpoint response contains the essential JSON keys:
    'data' (a non-empty list of artwork objects) and 'pagination' (dictionary).
    """
    res = client.get("/artworks")
    assert res["success"], f"Request failed: {res['error'] or ('status ' + str(res['status_code']))}"
    
    data = res["json"]
    assert isinstance(data, dict), "Response root must be a JSON object"
    assert "data" in data, "Response is missing mandatory field 'data'"
    assert "pagination" in data, "Response is missing mandatory field 'pagination'"
    
    assert isinstance(data["data"], list), "Field 'data' must be a list"
    assert len(data["data"]) > 0, "Field 'data' must contain at least one artwork object"
    assert isinstance(data["pagination"], dict), "Field 'pagination' must be a dictionary"


def test_artworks_fields(client):
    """
    Asserts that the artwork objects retrieved from the list endpoint contain
    all mandatory contract fields with their expected data types:
    id (integer), title (string), is_public_domain (boolean), and artist_title (string or null).
    """
    res = client.get("/artworks")
    assert res["success"], f"Request failed: {res['error']}"
    
    artworks = res["json"]["data"]
    # Check the first 5 elements to verify contract schema without spamming
    for i, art in enumerate(artworks[:5]):
        assert "id" in art, f"Artwork at index {i} is missing 'id'"
        assert isinstance(art["id"], int), f"Artwork ID at index {i} must be an integer, got {type(art['id'])}"
        
        assert "title" in art, f"Artwork at index {i} is missing 'title'"
        assert isinstance(art["title"], str), f"Artwork title at index {i} must be a string, got {type(art['title'])}"
        
        assert "is_public_domain" in art, f"Artwork at index {i} is missing 'is_public_domain'"
        assert isinstance(art["is_public_domain"], bool), f"Artwork 'is_public_domain' at index {i} must be a boolean, got {type(art['is_public_domain'])}"
        
        if art.get("artist_title") is not None:
            assert isinstance(art["artist_title"], str), f"Artwork 'artist_title' at index {i} must be a string, got {type(art['artist_title'])}"


def test_artwork_detail_valid(client):
    """
    Retrieves the details of a specific, known valid artwork ID.
    Asserts HTTP 200, checks response structure, and verifies that the returned
    object matches the requested ID and conforms to data type expectations.
    """
    # Use a well-known masterwork at Chicago Art Institute: 129696 (A Sunday on La Grande Jatte by Georges Seurat)
    valid_id = 129696
    res = client.get(f"/artworks/{valid_id}")
    if res["status_code"] is None:
        raise AssertionError(f"Network error: {res['error']}")
    
    assert res["status_code"] == 200, f"Expected 200, got {res['status_code']} for artwork ID {valid_id}"
    
    data = res["json"]
    assert isinstance(data, dict), "Response root must be a JSON object"
    assert "data" in data, "Response is missing 'data' node"
    
    art = data["data"]
    assert isinstance(art, dict), "Field 'data' must be a dictionary representing the artwork details"
    assert art.get("id") == valid_id, f"Expected artwork ID {valid_id}, got {art.get('id')}"
    assert isinstance(art.get("title"), str), f"Artwork title must be a string, got {type(art.get('title'))}"


def test_artwork_detail_invalid(client):
    """
    Performs a robustness test by requesting detail for a non-existent artwork (ID 99999999).
    Asserts that the Chicago Art Institute API gracefully returns a 404 Not Found error
    code along with a standard API error document.
    """
    invalid_id = 99999999
    res = client.get(f"/artworks/{invalid_id}")
    if res["status_code"] is None:
        raise AssertionError(f"Network error: {res['error']}")
    
    assert res["status_code"] == 404, f"Expected 404 Not Found, got {res['status_code']} for non-existent artwork"
    assert isinstance(res["json"], dict), "Error response should be a valid JSON dictionary"


def test_artwork_search_limit(client):
    """
    Performs a search request with query 'cats' and a limit of 3.
    Verifies HTTP 200 status, that search returns a list, and that it contains
    at most 3 items, satisfying pagination contract parameters.
    """
    params = {"q": "cats", "limit": 3}
    res = client.request("GET", "/artworks/search", params=params)
    if res["status_code"] is None:
        raise AssertionError(f"Network error: {res['error']}")
    
    assert res["status_code"] == 200, f"Expected 200, got {res['status_code']} for search query"
    
    data = res["json"]
    assert isinstance(data, dict), "Search response root must be a JSON object"
    assert "data" in data, "Search response is missing 'data' list"
    assert isinstance(data["data"], list), "Search response 'data' must be a list"
    
    count = len(data["data"])
    assert count <= 3, f"Expected search results count <= 3, got {count}"
    
    for i, item in enumerate(data["data"]):
        assert "_score" in item, f"Search result {i} is missing '_score'"
        assert isinstance(item["_score"], (int, float)), f"Search result {i} '_score' must be a number, got {type(item['_score'])}"
        assert "title" in item, f"Search result {i} is missing 'title'"
