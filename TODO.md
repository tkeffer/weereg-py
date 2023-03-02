Use a requirements.txt file.

Write a registration method that uses POST.

Tell flask it's behind a proxy: 
https://flask.palletsprojects.com/en/2.2.x/deploying/proxy_fix/

Allow API method /api/v2/stations to specify which fields are to be returned,
instead of all of them.

Maintain a blacklist on the nginx server.
See https://docs.nginx.com/nginx/admin-guide/security-controls/denylisting-ip-addresses/