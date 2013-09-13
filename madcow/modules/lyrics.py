"""Get song lyrics from lyricwiki"""

from urlparse import urlparse, urljoin, urlunparse
from urllib import urlencode
from cgi import parse_qsl
import re
from madcow.util import Module, strip_html
from madcow.util.http import getsoup
from madcow.util.google import Google, NonRedirectResponse
from madcow.util.text import *

def ipython():
    import sys
    # only call first time to protect from looping (shell traps SIGINT, very annoying and hard to escape)
    if not ipython.__dict__.get('x'):
        ipython.x = 1
        a, sys.argv[:] = sys.argv[:], ['ipython']
        try:
            from IPython.Shell import IPShellEmbed as S
            f = sys._getframe(1)
            S()('\nlocals: ' + ', '.join(sorted(f.f_locals)) if f.f_locals else '', f.f_locals, f.f_globals)
        finally:
            sys.argv[:] = a


class Main(Module):

    pattern = re.compile(r'^\s*sing\s+(.+?)\s*$', re.I)
    help = 'sing <song/artist/lyric>'
    error = "Couldn't find them, they must suck"

    def init(self):
        self.google = Google()

    def response(self, nick, args, kwargs):
        url = urlunparse(('https', 'www.google.com', 'search', '',
            urlencode({'num': '100', 'safe': 'off', 'hl': 'en', 'q': 'site:songmeanings.net ' + args[0]}), ''))
        soup = getsoup(url)
        new = None
        for h3 in soup.findAll('h3', attrs={'class': 'r'}):
            uri = urlparse(h3.a['href'])
            if uri.path == '/url':
                url = dict(parse_qsl(uri.query))['q']
                uri = urlparse(url)
                if re.search('/songs/view/\d+', uri.path) is not None:
                    new = urlunparse(uri._replace(query='', fragment=''))
                    break
                elif re.search('/profiles/(submissions|interaction)/\d+/comments', uri.path) is not None:
                    soup = getsoup(url)
                    for a in soup.find('a', title='Direct link to comment'):
                        new = urlunparse(urlparse(a.parent['href'])._replace(fragment='', query=''))
                        break
                if new:
                    break
        if new:
            url = new
            #try:
            #    url = self.google.lucky(u'site:songmeanings.net ' + args[0])
            #except NonRedirectResponse:
            #    self.log.warn('no url for query {0!r} found from google lucky'.format(args[0]))
            #    return u'{nick}: {error}'.format(error=self.error, **kwargs)

            ## XXX sometimes the only google link is to a comment on the thread for some reason beyond my ken
            #uri = urlparse(url)
            #if re.search('/profiles/interaction/\d+/comments', uri.path) is not None:
            #    soup = getsoup(url)
            #    for a in soup.find('a', title='Direct link to comment'):
            #        url = urlunparse(urlparse(a.parent['href'])._replace(fragment='', query=''))
            #        break

            try:
                soup = getsoup(url)
                try:
                    title = re.sub('\s+Lyrics\s+\|\s+SongMeanings.*$', '', soup.title.renderContents())
                    #title = strip_html(soup.find('a', 'pw_title').renderContents()).strip()
                except StandardError:
                    title = 'Unknown artist/song, check parsing code!'
                    #ipython()
                text = soup.find('div', id='textblock')
            except StandardError:
                self.log.warn('unable to find textblock from url {0!r} (query: {1!r})'.format(url, args[0]))
                return u'{nick}: {error}'.format(error=self.error, **kwargs)

            try:
                lyrics = decode(text.renderContents(), 'utf-8')
                return u'\n'.join(['[{}]'.format(title)] + filter(None, [line.strip() for line in strip_html(lyrics).splitlines()]))
            except StandardError:
                self.log.exception('error parsing lyrics for query: {0!r}'.format(args[0]))
                return u'{nick}: {error}'.format(error=self.error, **kwargs)
