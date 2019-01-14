"""
In this file the various text notebooks formats are defined. Please contribute
new formats here!
"""

import os
import re
from copy import copy
from .header import header_to_metadata_and_cell, insert_or_test_version_number
from .cell_reader import MarkdownCellReader, RMarkdownCellReader, \
    LightScriptCellReader, RScriptCellReader, DoublePercentScriptCellReader, HydrogenCellReader, \
    SphinxGalleryScriptCellReader
from .cell_to_text import MarkdownCellExporter, RMarkdownCellExporter, \
    LightScriptCellExporter, RScriptCellExporter, DoublePercentCellExporter, \
    HydrogenCellExporter, SphinxGalleryCellExporter
from .stringparser import StringParser
from .languages import _SCRIPT_EXTENSIONS


class JupytextFormatError(ValueError):
    """Error in the specification of the format for the text notebook"""
    pass


class NotebookFormatDescription:
    """Description of a notebook format"""

    def __init__(self,
                 format_name,
                 extension,
                 header_prefix,
                 cell_reader_class,
                 cell_exporter_class,
                 current_version_number,
                 min_readable_version_number=None):
        self.format_name = format_name
        self.extension = extension
        self.header_prefix = header_prefix
        self.cell_reader_class = cell_reader_class
        self.cell_exporter_class = cell_exporter_class
        self.current_version_number = current_version_number
        self.min_readable_version_number = min_readable_version_number


JUPYTEXT_FORMATS = \
    [
        NotebookFormatDescription(
            format_name='markdown',
            extension='.md',
            header_prefix='',
            cell_reader_class=MarkdownCellReader,
            cell_exporter_class=MarkdownCellExporter,
            # Version 1.0 on 2018-08-31 - jupytext v0.6.0 : Initial version
            current_version_number='1.0'),

        NotebookFormatDescription(
            format_name='rmarkdown',
            extension='.Rmd',
            header_prefix='',
            cell_reader_class=RMarkdownCellReader,
            cell_exporter_class=RMarkdownCellExporter,
            # Version 1.0 on 2018-08-22 - jupytext v0.5.2 : Initial version
            current_version_number='1.0')] + \
    [
        NotebookFormatDescription(
            format_name='spin',
            extension=ext,
            header_prefix="#'",
            cell_reader_class=RScriptCellReader,
            cell_exporter_class=RScriptCellExporter,
            # Version 1.0 on 2018-08-22 - jupytext v0.5.2 : Initial version
            current_version_number='1.0') for ext in ['.r', '.R']] + \
    [
        NotebookFormatDescription(
            format_name='light',
            extension=ext,
            header_prefix=_SCRIPT_EXTENSIONS[ext]['comment'],
            cell_reader_class=LightScriptCellReader,
            cell_exporter_class=LightScriptCellExporter,
            # Version 1.3 on 2018-09-22 - jupytext v0.7.0rc0 : Metadata are
            # allowed for all cell types (and then include 'cell_type')
            # Version 1.2 on 2018-09-05 - jupytext v0.6.3 : Metadata bracket
            # can be omitted when empty, if previous line is empty #57
            # Version 1.1 on 2018-08-25 - jupytext v0.6.0 : Cells separated
            # with one blank line #38
            # Version 1.0 on 2018-08-22 - jupytext v0.5.2 : Initial version
            current_version_number='1.3',
            min_readable_version_number='1.1') for ext in _SCRIPT_EXTENSIONS] + \
    [
        NotebookFormatDescription(
            format_name='percent',
            extension=ext,
            header_prefix=_SCRIPT_EXTENSIONS[ext]['comment'],
            cell_reader_class=DoublePercentScriptCellReader,
            cell_exporter_class=DoublePercentCellExporter,
            # Version 1.2 on 2018-11-18 - jupytext v0.8.6: Jupyter magics are commented by default #126, #132
            # Version 1.1 on 2018-09-23 - jupytext v0.7.0rc1 : [markdown] and
            # [raw] for markdown and raw cells.
            # Version 1.0 on 2018-09-22 - jupytext v0.7.0rc0 : Initial version
            current_version_number='1.2',
            min_readable_version_number='1.1') for ext in _SCRIPT_EXTENSIONS] + \
    [
        NotebookFormatDescription(
            format_name='hydrogen',
            extension=ext,
            header_prefix=_SCRIPT_EXTENSIONS[ext]['comment'],
            cell_reader_class=HydrogenCellReader,
            cell_exporter_class=HydrogenCellExporter,
            # Version 1.2 on 2018-12-14 - jupytext v0.9.0: same as percent - only magics are not commented by default
            current_version_number='1.2',
            min_readable_version_number='1.1') for ext in _SCRIPT_EXTENSIONS] + \
    [
        NotebookFormatDescription(
            format_name='sphinx',
            extension='.py',
            header_prefix='#',
            cell_reader_class=SphinxGalleryScriptCellReader,
            cell_exporter_class=SphinxGalleryCellExporter,
            # Version 1.0 on 2018-09-22 - jupytext v0.7.0rc0 : Initial version
            current_version_number='1.1')
    ]

NOTEBOOK_EXTENSIONS = list(dict.fromkeys(['.ipynb'] + [fmt.extension for fmt in JUPYTEXT_FORMATS]))
EXTENSION_PREFIXES = ['.lgt', '.spx', '.pct', '.hyd', '.nb']


def get_format_implementation(ext, format_name=None):
    """Return the implementation for the desired format"""
    # remove pre-extension if any
    ext = '.' + ext.split('.')[-1]

    if ext.endswith('.ipynb'):
        return None

    formats_for_extension = []
    for fmt in JUPYTEXT_FORMATS:
        if fmt.extension == ext:
            if fmt.format_name == format_name or not format_name:
                return fmt
            formats_for_extension.append(fmt.format_name)

    if formats_for_extension:
        raise TypeError("Format '{}' is not associated to extension '{}'. "
                        "Please choose one of: {}.".format(format_name, ext, ', '.join(formats_for_extension)))
    raise TypeError("Not format associated to extension '{}'".format(ext))


def read_metadata(text, ext):
    """Return the header metadata"""
    ext = '.' + ext.split('.')[-1]
    lines = text.splitlines()

    if ext in ['.md', '.Rmd']:
        comment = ''
    else:
        comment = _SCRIPT_EXTENSIONS.get(ext, {}).get('comment', '#')

    metadata, _, _, _ = header_to_metadata_and_cell(lines, comment)
    if ext in ['.r', '.R'] and not metadata:
        metadata, _, _, _ = header_to_metadata_and_cell(lines, "#'")

    return metadata


def read_format_from_metadata(text, ext):
    """Return the format of the file, when that information is available from the metadata"""
    metadata = read_metadata(text, ext)
    rearrange_jupytext_metadata(metadata)
    return format_name_for_ext(metadata, ext, explicit_default=False)


def guess_format(text, ext):
    """Guess the format of the file, given its extension and content"""
    lines = text.splitlines()

    metadata = read_metadata(text, ext)

    if ('jupytext' in metadata and set(metadata['jupytext'])
            .difference(['encoding', 'executable', 'main_language'])) or \
            set(metadata).difference(['jupytext']):
        return format_name_for_ext(metadata, ext)

    # Is this a Hydrogen-like script?
    # Or a Sphinx-gallery script?
    if ext in _SCRIPT_EXTENSIONS:
        comment = _SCRIPT_EXTENSIONS[ext]['comment']
        twenty_hash = ''.join(['#'] * 20)
        magic_re = re.compile(r'^(%|%%|%%%)[a-zA-Z]')
        double_percent_re = re.compile(r'^{}( %%|%%)$'.format(comment))
        double_percent_and_space_re = re.compile(r'^{}( %%|%%)\s'.format(comment))
        nbconvert_script_re = re.compile(r'^{}( <codecell>| In\[[0-9 ]*\]:?)'.format(comment))
        twenty_hash_count = 0
        double_percent_count = 0
        magic_command_count = 0

        parser = StringParser(language='R' if ext in ['.r', '.R'] else 'python')
        for line in lines:
            parser.read_line(line)
            if parser.is_quoted():
                continue

            # Don't count escaped Jupyter magics (no space between %% and command) as cells
            if double_percent_re.match(line) or double_percent_and_space_re.match(line) or \
                    nbconvert_script_re.match(line):
                double_percent_count += 1

            if magic_re.match(line):
                magic_command_count += 1

            if line.startswith(twenty_hash) and ext == '.py':
                twenty_hash_count += 1

        if double_percent_count >= 1:
            if magic_command_count:
                return 'hydrogen'
            return 'percent'

        if twenty_hash_count >= 2:
            return 'sphinx'

    # Default format
    return get_format_implementation(ext).format_name


def check_file_version(notebook, source_path, outputs_path):
    """Raise if file version in source file would override outputs"""
    if not insert_or_test_version_number():
        return

    _, ext = os.path.splitext(source_path)
    if ext.endswith('.ipynb'):
        return
    version = notebook.metadata.get('jupytext', {}).get('text_representation', {}).get('format_version')
    format_name = format_name_for_ext(notebook.metadata, ext)

    fmt = get_format_implementation(ext, format_name)
    current = fmt.current_version_number

    # Missing version, still generated by jupytext?
    if notebook.metadata and not version:
        version = current

    # Same version? OK
    if version == fmt.current_version_number:
        return

    # Version larger than minimum readable version
    if (fmt.min_readable_version_number or current) <= version <= current:
        return

        # Not merging? OK
    if source_path == outputs_path:
        return

    raise ValueError("File {} has jupytext_format_version={}, but "
                     "current version for that extension is {}.\n"
                     "It would not be safe to override the source of {} "
                     "with that file.\n"
                     "Please remove one or the other file."
                     .format(os.path.basename(source_path),
                             version, current,
                             os.path.basename(outputs_path)))


def parse_one_format(ext_and_format_name):
    """Parse "py:percent" into (".py", "percent"), etc"""
    if ext_and_format_name.find(':') >= 0:
        ext, format_name = ext_and_format_name.split(':', 1)
    else:
        ext = ext_and_format_name
        format_name = None

    if not ext.startswith('.'):
        ext = '.' + ext

    legitimate_extensions = NOTEBOOK_EXTENSIONS + ['.auto']
    if ext in legitimate_extensions:
        return ext, format_name

    if ext.rfind('.') > 0:
        pre, short_ext = os.path.splitext(ext)
        if short_ext in legitimate_extensions and pre in EXTENSION_PREFIXES:
            return ext, format_name

    raise ValueError("Extension '{}' should have been one of '{}', with optional prefix among '{}'".format(
        ext, "','".join(legitimate_extensions), "','".join(EXTENSION_PREFIXES)))


def parse_formats(formats):
    """Parse "md,py:percent" into [(".md", None), (".py", "percent")], etc"""
    if not formats:
        return []
    return [parse_one_format(ext_and_format_name)
            for ext_and_format_name in formats.split(',')]


def update_formats(formats, ext, format_name):
    """Update the format list with the given format name"""
    updated_formats = []
    found_ext = False
    for org_ext, org_format_name in formats:
        if org_ext != ext:
            updated_formats.append((org_ext, org_format_name))
        elif not found_ext:
            updated_formats.append((ext, format_name))
            found_ext = True

    return updated_formats


def one_format_as_string(ext, format_name):
    """('.py', None) to 'py', etc"""
    if ext.startswith('.'):
        ext = ext[1:]
    if format_name and format_name not in ['markdown', 'rmarkdown']:
        return ext + ':' + format_name
    return ext


def formats_as_string(formats):
    """Concatenate all formats into a string"""
    return ','.join([one_format_as_string(ext, format_name)
                     for ext, format_name in formats])


def auto_ext_from_metadata(metadata):
    """Script extension from kernel information"""
    auto_ext = metadata.get('language_info', {}).get('file_extension')
    if auto_ext == '.r':
        return '.R'
    return auto_ext


def format_name_for_ext(metadata, ext, cm_default_formats=None, explicit_default=True):
    """Return the format name for that extension"""

    # Is the format information available in the text representation?
    text_repr = metadata.get('jupytext', {}).get('text_representation')
    if text_repr and text_repr.get('extension') == ext and text_repr.get('format_name'):
        return text_repr.get('format_name')

    # Format from jupytext.formats
    auto_ext = auto_ext_from_metadata(metadata)
    formats = metadata.get('jupytext', {}).get('formats', '') or cm_default_formats
    formats = parse_formats(formats)
    for fmt_ext, ext_format_name in formats:
        if fmt_ext.endswith(ext) or (fmt_ext.endswith('.auto') and auto_ext and ext.endswith(auto_ext)):
            if (not explicit_default) or ext_format_name:
                return ext_format_name

    if (not explicit_default) or ext in ['.Rmd', '.md']:
        return None

    return get_format_implementation(ext).format_name


def update_jupytext_formats_metadata(notebook, ext, format_name):
    """Update the jupytext_format metadata in the Jupyter notebook"""
    formats = parse_formats(notebook.metadata.get('jupytext', {}).get('formats', ''))
    formats = update_formats(formats, ext, format_name)
    if formats:
        notebook.metadata.setdefault('jupytext', {})['formats'] = formats_as_string(formats)


def rearrange_jupytext_metadata(metadata):
    """Convert the jupytext_formats metadata entry to jupytext/formats, etc. See #91"""

    # Backward compatibility with nbrmd
    for key in ['nbrmd_formats', 'nbrmd_format_version']:
        if key in metadata:
            metadata[key.replace('nbrmd', 'jupytext')] = metadata.pop(key)

    jupytext_metadata = metadata.pop('jupytext', {})

    if 'jupytext_formats' in metadata:
        jupytext_metadata['formats'] = metadata.pop('jupytext_formats')
    if 'jupytext_format_version' in metadata:
        jupytext_metadata['text_representation'] = {'format_version': metadata.pop('jupytext_format_version')}
    if 'main_language' in metadata:
        jupytext_metadata['main_language'] = metadata.pop('main_language')
    for entry in ['encoding', 'executable']:
        if entry in metadata:
            jupytext_metadata[entry] = metadata.pop(entry)

    filters = jupytext_metadata.pop('metadata_filter', {})
    if 'notebook' in filters:
        jupytext_metadata['notebook_metadata_filter'] = filters['notebook']
    if 'cells' in filters:
        jupytext_metadata['cell_metadata_filter'] = filters['cells']

    for filter_level in ['notebook_metadata_filter', 'cell_metadata_filter']:
        if isinstance(jupytext_metadata.get(filter_level), dict):
            additional = jupytext_metadata.get(filter_level).get('additional', [])
            if additional == 'all':
                entries = ['all']
            else:
                entries = additional

            excluded = jupytext_metadata.get(filter_level).get('excluded', [])
            if excluded == 'all':
                entries.append('-all')
            else:
                entries.extend(['-' + e for e in excluded])

            jupytext_metadata[filter_level] = ','.join(entries)

    if jupytext_metadata:
        metadata['jupytext'] = jupytext_metadata


def long_form_one_format(jupytext_format):
    """Parse 'sfx.py:percent' into {'suffix':'sfx', 'extension':'py', 'format_name':'percent'}"""
    if not isinstance(jupytext_format, str):
        return jupytext_format

    if jupytext_format.find(':') >= 0:
        ext, format_name = jupytext_format.split(':', 1)
        jupytext_format = {'format_name': format_name}
    else:
        ext = jupytext_format
        jupytext_format = {}

    if ext.rfind('.') > 0:
        jupytext_format['suffix'], ext = os.path.splitext(ext)

    if not ext.startswith('.'):
        ext = '.' + ext

    jupytext_format['extension'] = ext
    return jupytext_format


def long_form_multiple_formats(jupytext_formats):
    """Convert a concise encoding of jupytext.formats to a list of formats, encoded as dictionaries"""
    if not jupytext_formats:
        return []

    if isinstance(jupytext_formats, str):
        jupytext_formats = [fmt for fmt in jupytext_formats.split(',') if fmt]

    jupytext_formats = [long_form_one_format(fmt) for fmt in jupytext_formats]

    for fmt in jupytext_formats:
        validate_one_format(fmt)

    return jupytext_formats


_VALID_FORMAT_OPTIONS = ['extension', 'format_name', 'suffix', 'prefix', 'comment_magics',
                         'split_at_heading', 'notebook_metadata_filter', 'cell_metadata_filter']
_BINARY_FORMAT_OPTIONS = ['comment_magics', 'split_at_heading']


def validate_one_format(jupytext_format):
    """Validate extension and options for the given format"""
    if not isinstance(jupytext_format, dict):
        raise JupytextFormatError('Jupytext format should be a dictionary')

    for key in jupytext_format:
        if key not in _VALID_FORMAT_OPTIONS:
            raise JupytextFormatError("Unknown format option '{}' - should be one of '{}'".format(
                key, "', '".join(_VALID_FORMAT_OPTIONS)))
        value = jupytext_format[key]
        if key in _BINARY_FORMAT_OPTIONS:
            if not isinstance(value, bool):
                raise JupytextFormatError("Format option '{}' should be a bool, not '{}'".format(key, str(value)))
        elif not isinstance(value, str):
            raise JupytextFormatError("Format option '{}' should be a string, not '{}'".format(key, str(value)))

    if 'extension' not in jupytext_format:
        raise JupytextFormatError('Missing format extension')
    ext = jupytext_format['extension']
    if ext not in NOTEBOOK_EXTENSIONS + ['.auto']:
        raise JupytextFormatError("Extension '{}' is not a notebook extension. Please use one of '{}'.".format(
            ext, "', '".join(NOTEBOOK_EXTENSIONS + ['.auto'])))


def set_auto_ext(jupytext_formats, metadata):
    """Expend the format definition, and replaces extension .auto with that from the metadata"""
    jupytext_formats = long_form_multiple_formats(jupytext_formats)
    ext = auto_ext_from_metadata(metadata)

    for fmt in jupytext_formats:
        if fmt['extension'] == '.auto':
            if not ext:
                raise ValueError('No kernel information found, cannot save to .auto extension')
            fmt['extension'] = ext

    return jupytext_formats


def identical_format_path(fmt1, fmt2):
    """Do the two (long representation) of formats target the same file?"""
    for key in ['extension', 'prefix', 'suffix']:
        if fmt1.get(key) != fmt2.get(key):
            return False
    return True


# TODO: remove this function
def _fmt_from_ext_and_format_name(ext, format_name, format_options=None):
    fmt = copy(format_options) if format_options else {}
    if format_name:
        fmt['format_name'] = format_name
    if ext.rfind('.'):
        suffix, ext = os.path.splitext(ext)
        fmt['suffix'] = suffix
    fmt['extension'] = ext
    return fmt
