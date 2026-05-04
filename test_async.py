import requests
import time

# Test async analysis
print("Starting analysis...")
response = requests.post(
    'http://localhost:8000/api/analyze/compas-scores-two-years.csv',
    params={
        'target_column': 'two_year_recid',
        'sensitive_attributes': ['race', 'sex']
    }
)
print(f"Analysis start response: {response.status_code}")
data = response.json()
print(f"Response: {data}")

if 'job_id' in data:
    job_id = data['job_id']
    print(f"Job ID: {job_id}")

    # Poll for status
    for i in range(30):  # Poll for up to 30 seconds
        time.sleep(2)
        status_response = requests.get(f'http://localhost:8000/api/status/{job_id}')
        if status_response.status_code == 200:
            status_data = status_response.json()
            print(f"Progress: {status_data['progress']}%, Message: {status_data['message']}")
            if status_data['status'] == 'completed':
                print("Analysis completed!")
                break
            elif status_data['status'] == 'error':
                print(f"Analysis failed: {status_data['message']}")
                break
        else:
            print(f"Status check failed: {status_response.status_code}")
else:
    print("No job ID returned")
