"""Exposes the app to a WSGI server."""
import weereg
import pprint


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

# Uncomment the following and run from the command line to print details about
# every request:
# weereg.wsgi_app = PrintingMiddleware(weereg.wsgi_app)

if __name__ == '__main__':
    # We are not being run in a WSGI server. Just run the app directly.
    weereg.run()
