import time
import math
import datetime
from tester.client import ChicagoArtInstituteClient
from tester.tests import (
    test_artworks_list_status,
    test_artworks_list_structure,
    test_artworks_fields,
    test_artwork_detail_valid,
    test_artwork_detail_invalid,
    test_artwork_search_limit
)

def get_p95(latencies):
    if not latencies:
        return 0.0
    sorted_lats = sorted(latencies)
    # 95th percentile index calculation
    idx = int(len(sorted_lats) * 0.95)
    # Ensure index is within boundaries
    idx = min(max(0, idx), len(sorted_lats) - 1)
    return sorted_lats[idx]

def run_all_tests():
    client = ChicagoArtInstituteClient()
    
    test_cases = [
        ("GET /artworks Status & Content-Type", test_artworks_list_status),
        ("GET /artworks JSON Contract Structure", test_artworks_list_structure),
        ("GET /artworks Fields and Data Types", test_artworks_fields),
        ("GET /artworks/{id} Valid Artwork Details", test_artwork_detail_valid),
        ("GET /artworks/{id} Non-existent Artwork 404", test_artwork_detail_invalid),
        ("GET /artworks/search Query Limit Constraint", test_artwork_search_limit)
    ]
    
    results = []
    latencies = []
    passed = 0
    failed = 0
    
    for name, test_func in test_cases:
        start_time = time.perf_counter()
        status = "PASS"
        details = None
        
        try:
            test_func(client)
            passed += 1
        except AssertionError as ae:
            status = "FAIL"
            details = str(ae)
            failed += 1
        except Exception as e:
            status = "FAIL"
            details = f"Unexpected execution error: {str(e)}"
            failed += 1
            
        test_duration = (time.perf_counter() - start_time) * 1000.0
        latencies.append(test_duration)
        
        results.append({
            "name": name,
            "status": status,
            "latency_ms": test_duration,
            "details": details
        })
    
    # Calculate QoS Summaries
    total_tests = len(test_cases)
    error_rate = failed / total_tests if total_tests > 0 else 0.0
    latency_avg = sum(latencies) / total_tests if total_tests > 0 else 0.0
    latency_p95 = get_p95(latencies)
    
    # Availability can be defined as percentage of successful test cases
    availability = passed / total_tests if total_tests > 0 else 0.0
    
    # Extract some sample artworks from the Chicago Art Institute to showcase on the dashboard (WOW factor)
    featured_artworks = []
    try:
        # Fetch artworks list to extract images and titles
        res = client.get("/artworks?limit=6")
        if res["success"] and res["json"] and "data" in res["json"]:
            art_data = res["json"]["data"]
            iiif_base_url = "https://www.artic.edu/iiif/2"
            
            # Look up config node to build correct IIIF url if present
            if "config" in res["json"] and "iiif_url" in res["json"]["config"]:
                iiif_base_url = res["json"]["config"]["iiif_url"]
                
            for art in art_data:
                image_id = art.get("image_id")
                if image_id:
                    # Construct direct image URL via Chicago Art Institute IIIF CDN
                    image_url = f"{iiif_base_url}/{image_id}/full/400,/0/default.jpg"
                    featured_artworks.append({
                        "artwork_id": art.get("id"),
                        "title": art.get("title", "Unknown Title"),
                        "artist": art.get("artist_title", "Unknown Artist") or "Unknown Artist",
                        "image_url": image_url,
                        "is_public": 1 if art.get("is_public_domain") else 0
                    })
    except Exception as e:
        # Graceful fallback, won't break the runner
        print(f"Failed to gather featured artworks: {e}")
        
    # If API call failed or returned no images, add a beautiful static fallback
    if not featured_artworks:
        featured_artworks = [
            {
                "artwork_id": 129696,
                "title": "A Sunday on La Grande Jatte",
                "artist": "Georges Seurat",
                "image_url": "https://www.artic.edu/iiif/2/1adef906-cf6d-ab4e-bf2c-0e78c8e10f1b/full/400,/0/default.jpg",
                "is_public": 1
            }
        ]
        
    payload = {
        "api": "Art Institute of Chicago",
        "timestamp": datetime.datetime.now().astimezone().isoformat(),
        "summary": {
            "passed": passed,
            "failed": failed,
            "error_rate": error_rate,
            "latency_ms_avg": latency_avg,
            "latency_ms_p95": latency_p95,
            "availability": availability
        },
        "tests": results,
        "artworks": featured_artworks[:4] # Store top 4 for the dashboard
    }
    
    return payload
