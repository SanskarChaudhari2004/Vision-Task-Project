from vision_task import create_app

app = create_app()
app.testing = True
client = app.test_client()

with client.session_transaction() as sess:
    sess['username'] = 'admin'

res = client.post(
    '/users/create',
    data={'username': 'testuser', 'password': 'Test1234!', 'department': 'Clinic', 'roles': ['user']},
    follow_redirects=True,
)

print('status', res.status_code)
print(res.data.decode()[:1000])
