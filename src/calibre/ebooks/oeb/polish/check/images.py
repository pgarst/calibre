#!/usr/bin/env python
# vim:fileencoding=utf-8
from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

__license__ = 'GPL v3'
__copyright__ = '2013, Kovid Goyal <kovid at kovidgoyal.net>'

from calibre import as_unicode
from calibre.utils.magick import Image
from calibre.ebooks.oeb.polish.check.base import BaseError, WARN
from calibre.ebooks.oeb.polish.check.parsing import EmptyFile

class InvalidImage(BaseError):

    HELP = _('An invalid image is an image that could not be loaded, typically because'
             ' it is corrupted. You should replace it with a good image or remove it.')

    def __init__(self, msg, *args, **kwargs):
        BaseError.__init__(self, 'Invalid image: ' + msg, *args, **kwargs)

class CMYKImage(BaseError):

    HELP = _('Reader devices based on Adobe Digital Editions cannot display images whose'
             ' colors are specified in the CMYK colorspace. You should convert this image'
             ' to the RGB colorspace, for maximum compatibility.')
    INDIVIDUAL_FIX = _('Convert image to RGB automatically')
    level = WARN

    def __call__(self, container):
        from PyQt4.Qt import QImage
        from calibre.gui2 import pixmap_to_data
        ext = container.mime_map[self.name].split('/')[-1].upper()
        if ext == 'JPG':
            ext = 'JPEG'
        if ext not in ('PNG', 'JPEG', 'GIF'):
            return False
        with container.open(self.name, 'r+b') as f:
            raw = f.read()
            i = QImage()
            i.loadFromData(raw)
            if i.isNull():
                return False
            raw = pixmap_to_data(i, format=ext, quality=95)
            f.seek(0)
            f.truncate()
            f.write(raw)
        return True

def check_raster_images(name, mt, raw):
    if not raw:
        return [EmptyFile(name)]
    errors = []
    i = Image()
    try:
        i.load(raw)
    except Exception as e:
        errors.append(InvalidImage(as_unicode(e.message), name))
    else:
        if i.colorspace == 'CMYKColorspace':
            errors.append(CMYKImage(_('Image is in the CMYK colorspace'), name))

    return errors

