"""Exposes the app to a WSGI server."""
import weereg
import pprint

from werkzeug.middleware.proxy_fix import ProxyFix


class PrintingMiddleware(object):
    """Useful for printing every request."""

    def __init__(self, app):
        self._app = app

    def __call__(self, env, resp):
        pprint.pprint(f"Incoming environment: {env}")

        def log_response(status, headers, *args):
            pprint.pprint(f"Response status: {status}, headers: {headers}")
            return resp(status, headers, *args)

        return self._app(env, log_response)


# Create the app.
weereg = weereg.create_app()

# Make sure it uses the proxied headers, but only one level deep.
# See https://flask.palletsprojects.com/en/2.2.x/deploying/proxy_fix/
weereg.wsgi_app = ProxyFix(weereg.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# Uncomment the following to print details about every request:
# weereg.wsgi_app = PrintingMiddleware(weereg.wsgi_app)

if __name__ == '__main__':
    # We are not being run in a WSGI server. Just run the app directly.
    weereg.run()
