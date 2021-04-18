

from . import FontFile, Image

bdf_slant = {
    "R": "Roman",
    "I": "Italic",
    "O": "Oblique",
    "RI": "Reverse Italic",
    "RO": "Reverse Oblique",
    "OT": "Other",
}

bdf_spacing = {"P": "Proportional", "M": "Monospaced", "C": "Cell"}
# Taken from the Pillow project

# The Python Imaging Library (PIL) is
#
#     Copyright © 1997-2011 by Secret Labs AB
#     Copyright © 1995-2011 by Fredrik Lundh
#
# Pillow is the friendly PIL fork. It is
#
#     Copyright © 2010-2021 by Alex Clark and contributors
#
# Like PIL, Pillow is licensed under the open source HPND License:
#
# By obtaining, using, and/or copying this software and/or its associated
# documentation, you agree that you have read, understood, and will comply
# with the following terms and conditions:
#
# Permission to use, copy, modify, and distribute this software and its
# associated documentation for any purpose and without fee is hereby granted,
# provided that the above copyright notice appears in all copies, and that
# both that copyright notice and this permission notice appear in supporting
# documentation, and that the name of Secret Labs AB or the author not be
# used in advertising or publicity pertaining to distribution of the software
# without specific, written prior permission.
#
# SECRET LABS AB AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD TO THIS
# SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS.
# IN NO EVENT SHALL SECRET LABS AB OR THE AUTHOR BE LIABLE FOR ANY SPECIAL,
# INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM
# LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE
# OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
# PERFORMANCE OF THIS SOFTWARE.

# The Python Imaging Library
# $Id$
#
# bitmap distribution font (bdf) file parser
#
# history:
# 1996-05-16 fl   created (as bdf2pil)
# 1997-08-25 fl   converted to FontFile driver
# 2001-05-25 fl   removed bogus __init__ call
# 2002-11-20 fl   robustification (from Kevin Cazabon, Dmitry Vasiliev)
# 2003-04-22 fl   more robustification (from Graham Dumpleton)
#
# Copyright (c) 1997-2003 by Secret Labs AB.
# Copyright (c) 1997-2003 by Fredrik Lundh.
#
# See the README file for information on usage and redistribution.
#

"""
Parse X Bitmap Distribution Format (BDF)
"""


def bdf_char(f):
    # skip to STARTCHAR
    while True:
        s = f.readline()
        if not s:
            return None
        if s[:9] == b"STARTCHAR":
            break
    id = s[9:].strip().decode("ascii")

    # load symbol properties
    props = {}
    while True:
        s = f.readline()
        if not s or s[:6] == b"BITMAP":
            break
        i = s.find(b" ")
        props[s[:i].decode("ascii")] = s[i + 1 : -1].decode("ascii")

    # load bitmap
    bitmap = []
    while True:
        s = f.readline()
        if not s or s[:7] == b"ENDCHAR":
            break
        bitmap.append(s[:-1])
    bitmap = b"".join(bitmap)

    [x, y, l, d] = [int(p) for p in props["BBX"].split()]
    [dx, dy] = [int(p) for p in props["DWIDTH"].split()]

    bbox = (dx, dy), (l, -d - y, x + l, -d), (0, 0, x, y)

    try:
        im = Image.frombytes("1", (x, y), bitmap, "hex", "1")
    except ValueError:
        # deal with zero-width characters
        im = Image.new("1", (x, y))

    return id, int(props["ENCODING"]), bbox, im


class BdfFontFile(FontFile.FontFile):
    """Font file plugin for the X11 BDF format."""

    def __init__(self, fp):
        super().__init__()

        s = fp.readline()
        if s[:13] != b"STARTFONT 2.1":
            raise SyntaxError("not a valid BDF file")

        props = {}
        comments = []

        while True:
            s = fp.readline()
            if not s or s[:13] == b"ENDPROPERTIES":
                break
            i = s.find(b" ")
            props[s[:i].decode("ascii")] = s[i + 1 : -1].decode("ascii")
            if s[:i] in [b"COMMENT", b"COPYRIGHT"]:
                if s.find(b"LogicalFontDescription") < 0:
                    comments.append(s[i + 1 : -1].decode("ascii"))

        while True:
            c = bdf_char(fp)
            if not c:
                break
            id, ch, (xy, dst, src), im = c
            if 0 <= ch < len(self.glyph):
                self.glyph[ch] = xy, dst, src, im