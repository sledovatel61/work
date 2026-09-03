#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extract text from muk.docx with paragraph IDs, footnote anchors, sub/superscript marks, and table awareness. (stdlib version)"""
import re
import xml.etree.ElementTree as ET

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'

def qn(local):
    return '{%s}%s' % (W, local)

def qname(tag):
    return tag.split('}')[-1] if '}' in tag else tag

def iter_text_of_runs(container):
    parts = []
    for node in container.iter():
        tag = qname(node.tag)
        if tag == 'footnoteReference':
            fid = node.get(qn('id'))
            parts.append('[[FN%s]]' % fid)
        elif tag == 'endnoteReference':
            fid = node.get(qn('id'))
            parts.append('[[EN%s]]' % fid)
        elif tag == 'tab':
            parts.append('\t')
        elif tag == 'br':
            parts.append(' ')
        elif tag == 't':
            r = node
            va = None
            while r is not None:
                if qname(r.tag) == 'r':
                    rpr = r.find(qn('rPr'))
                    if rpr is not None:
                        va_el = rpr.find(qn('vertAlign'))
                        if va_el is not None:
                            va = va_el.get(qn('val'))
                    break
                r = r.getparent() if hasattr(r, 'getparent') else None
            txt = node.text or ''
            if va == 'superscript':
                parts.append('^' + txt + '^')
            elif va == 'subscript':
                parts.append('{' + txt + '}')
            else:
                parts.append(txt)
    return ''.join(parts)

def main():
    path = '/home/user/work/work_agent4/docx_extract/word/document.xml'
    tree = ET.parse(path)
    body = tree.getroot().find(qn('body'))
    out = []
    state = {'pidx': 0, 'tbl': 0}

    def walk(container):
        for child in list(container):
            tag = qname(child.tag)
            if tag == 'p':
                state['pidx'] += 1
                txt = iter_text_of_runs(child).strip()
                txt = re.sub(r'[ \t]+', ' ', txt)
                style = ''
                ppr = child.find(qn('pPr'))
                if ppr is not None:
                    ps = ppr.find(qn('pStyle'))
                    if ps is not None:
                        style = ps.get(qn('val')) or ''
                if txt:
                    prefix = '[P%04d]' % state['pidx']
                    if style:
                        prefix += '{%s}' % style
                    out.append(prefix + ' ' + txt)
            elif tag == 'tbl':
                state['tbl'] += 1
                t = state['tbl']
                out.append('')
                out.append('===== TABLE %d =====' % t)
                for row in child.findall(qn('tr')):
                    cells = []
                    for tc in row.findall(qn('tc')):
                        ctxt = ' '.join(iter_text_of_runs(p).strip() for p in tc.findall(qn('p')))
                        ctxt = re.sub(r'\s+', ' ', ctxt).strip()
                        cells.append(ctxt)
                    out.append('TBL%04d | ' % t + ' || '.join(cells))
                out.append('===== END TABLE %d =====' % t)
                out.append('')
            elif tag == 'sdt':
                sdt_content = child.find(qn('sdtContent'))
                if sdt_content is not None:
                    walk(sdt_content)

    walk(body)
    with open('/home/user/work/work_agent4/docx_text.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(out))

    ft = ET.parse('/home/user/work/work_agent4/docx_extract/word/footnotes.xml')
    fout = []
    for fn in ft.getroot().findall(qn('footnote')):
        fid = fn.get(qn('id'))
        txt = ' '.join(iter_text_of_runs(p).strip() for p in fn.findall(qn('p')))
        txt = re.sub(r'\s+', ' ', txt).strip()
        fout.append('[[FN%s]] %s' % (fid, txt))
    with open('/home/user/work/work_agent4/footnotes.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(fout))
    print('paragraphs:', state['pidx'], 'tables:', state['tbl'])

if __name__ == '__main__':
    main()
