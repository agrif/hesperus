from ..plugin import PassivePlugin
from ..shorturl import short_url

import requests

class SteamLinkPlugin(PassivePlugin):
    STOREFRONT_API_ENDPOINT = 'https://store.steampowered.com/api/{api_method}/'

    @PassivePlugin.config_types(country_code=str, language=str)
    def __init__(self, core, country_code='US', language='english', *args):
        super(SteamLinkPlugin, self).__init__(core, *args)

        self._cc = country_code
        self._lang = language

    @PassivePlugin.register_pattern(r'(?:https?://)?store.steampowered.com/app/(?P<app_id>\d+)/?')
    def find_steam_link(self, match, reply):
        app_id = match.group(1)
        try:
            app_details = self._get_app_details(app_id)
        except Exception as err:
            # self.log_warn(err)
            return
        else:
            reply(self._format_reply(app_details))

    def _format_reply(self, app_details):
        r = 'Steam: "{}" '.format(app_details['name'].encode('ascii', 'ignore'))
        r += u'on ' + ', '.join(k.title() for k, v in app_details['platforms'].iteritems() if v) + ' '
        try:
            if app_details['release_date']['coming_soon']:
                r += '(releases on: {}) '.format(app_details['release_date']['date'])
        except KeyError: pass
        if app_details['is_free']:
            r += '(FREE) '
        else:
            r += '@ {0} {1} '.format(app_details['price_overview']['final'] / 100.0, app_details['price_overview']['currency'])
        r += '<{}> '.format(short_url(app_details['website']))
        return r

    def _get_app_details(self, app_id):
        resp_data = self._api_request('appdetails', appids=app_id, cc=self._cc, l=self._lang)
        # KeyErrors are caught in calling method
        app_details = resp_data[app_id]['data']
        return app_details

    def _api_request(self, method, **kwargs):
        url = self.STOREFRONT_API_ENDPOINT.format(api_method=method)
        return requests.get(url, params=kwargs).json()
