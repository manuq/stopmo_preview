Translations welcome.  Send me the texts.

Here are the commands I always forget:

# Update catalog

    xgettext --language=Python --keyword=_ --output messages.pot `find ../src -name "*.py"`

# Start a new translation

    msginit --input=messages.pot --locale=es

# Update a translation

    msgmerge --update --backup=off es.po messages.pot

# Compile a translation

    msgfmt es.po --output-file ../src/locale/es/LC_MESSAGES/stopmo_preview.mo
