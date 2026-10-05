import os
import shutil
import tempfile
import zipfile
import lxml.etree as ET
import pytest

from packages.replacement_engine.package_engine import PackageLevelDocxEngine, NS

def create_test_docx(paragraphs_xml_list: list) -> str:
    """Creates a minimal valid DOCX with the given paragraph XML strings."""
    temp_dir = tempfile.mkdtemp(prefix="test_docx_")
    docx_path = os.path.join(temp_dir, "test.docx")
    
    body_content = "\n".join(paragraphs_xml_list)
    doc_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
            xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <w:body>
    {body_content}
    <w:sectPr>
      <w:pgSz w:w="12240" w:h="15840"/>
    </w:sectPr>
  </w:body>
</w:document>"""

    content_types_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"""

    rels_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""

    with zipfile.ZipFile(docx_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types_xml)
        zf.writestr("_rels/.rels", rels_xml)
        zf.writestr("word/document.xml", doc_xml)
    
    return docx_path

def read_doc_text(docx_path: str) -> str:
    with zipfile.ZipFile(docx_path, "r") as zf:
        xml = zf.read("word/document.xml")
        root = ET.fromstring(xml)
        paras = []
        for p in root.xpath(".//w:p", namespaces=NS):
            t = "".join(p.xpath(".//w:t/text()", namespaces=NS))
            if t.strip():
                paras.append(t.strip())
        return "\n".join(paras)


def test_1_normal_title_replacement():
    """Test 1: Existing template title: 'AI Based Irrigation System' -> New project title: 'Ai based irrigation'"""
    p = """<w:p xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
        <w:r><w:rPr><w:b/><w:sz w:val="48"/></w:rPr><w:t>AI Based Irrigation System</w:t></w:r>
    </w:p>"""
    tpl = create_test_docx([p])
    out = os.path.join(tempfile.mkdtemp(), "out.docx")

    res = PackageLevelDocxEngine.replace(
        template_path=tpl,
        field_values={"project_title": "Ai based irrigation"},
        field_mapping=[{"arm_field": "project_title", "template_element": "AI Based Irrigation System", "action": "replace"}],
        output_path=out,
        job_id="test1",
    )
    assert res.success is True
    assert "project_title" in [a.field_name for a in res.audit if a.replaced]
    txt = read_doc_text(out)
    assert txt == "Ai based irrigation"


def test_2_title_split_across_multiple_runs():
    """Test 2: Existing template title split across multiple Word runs."""
    p = """<w:p xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
        <w:r><w:rPr><w:b/><w:sz w:val="48"/></w:rPr><w:t>AI </w:t></w:r>
        <w:r><w:rPr><w:b/><w:sz w:val="48"/></w:rPr><w:t>Based </w:t></w:r>
        <w:r><w:rPr><w:b/><w:sz w:val="48"/></w:rPr><w:t>Irrigation</w:t></w:r>
        <w:r><w:rPr><w:b/><w:sz w:val="48"/></w:rPr><w:t> System</w:t></w:r>
    </w:p>"""
    tpl = create_test_docx([p])
    out = os.path.join(tempfile.mkdtemp(), "out.docx")

    res = PackageLevelDocxEngine.replace(
        template_path=tpl,
        field_values={"project_title": "Ai based irrigation"},
        field_mapping=[{"arm_field": "project_title", "template_element": "AI Based Irrigation System", "action": "replace"}],
        output_path=out,
        job_id="test2",
    )
    assert res.success is True
    txt = read_doc_text(out)
    assert txt == "Ai based irrigation"


def test_3_title_contains_extra_spaces_and_newlines():
    """Test 3: Existing template title contains extra spaces / newlines."""
    p = """<w:p xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
        <w:r><w:rPr><w:b/><w:sz w:val="48"/></w:rPr><w:t>AI    Based  </w:t><w:br/><w:t>   Irrigation   System</w:t></w:r>
    </w:p>"""
    tpl = create_test_docx([p])
    out = os.path.join(tempfile.mkdtemp(), "out.docx")

    res = PackageLevelDocxEngine.replace(
        template_path=tpl,
        field_values={"project_title": "Ai based irrigation"},
        field_mapping=[{"arm_field": "project_title", "template_element": "AI Based Irrigation System", "action": "replace"}],
        output_path=out,
        job_id="test3",
    )
    assert res.success is True
    txt = read_doc_text(out)
    assert txt == "Ai based irrigation"


def test_4_different_capitalization():
    """Test 4: Existing template title has different capitalization."""
    p = """<w:p xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
        <w:r><w:rPr><w:b/><w:sz w:val="48"/></w:rPr><w:t>ai based irrigation system</w:t></w:r>
    </w:p>"""
    tpl = create_test_docx([p])
    out = os.path.join(tempfile.mkdtemp(), "out.docx")

    res = PackageLevelDocxEngine.replace(
        template_path=tpl,
        field_values={"project_title": "Ai based irrigation"},
        field_mapping=[{"arm_field": "project_title", "template_element": "AI Based Irrigation System", "action": "replace"}],
        output_path=out,
        job_id="test4",
    )
    assert res.success is True
    txt = read_doc_text(out)
    assert txt == "Ai based irrigation"


def test_5_different_project_title_no_irrigation_traces():
    """Test 5: Change project title to 'AI Based Attendance Management System' -> verify no irrigation remains."""
    p = """<w:p xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
        <w:r><w:rPr><w:b/><w:sz w:val="48"/></w:rPr><w:t>AI Based Irrigation System</w:t></w:r>
    </w:p>"""
    tpl = create_test_docx([p])
    out = os.path.join(tempfile.mkdtemp(), "out.docx")

    res = PackageLevelDocxEngine.replace(
        template_path=tpl,
        field_values={"project_title": "AI Based Attendance Management System"},
        field_mapping=[{"arm_field": "project_title", "template_element": "AI Based Irrigation System", "action": "replace"}],
        output_path=out,
        job_id="test5",
    )
    assert res.success is True
    txt = read_doc_text(out)
    assert txt == "AI Based Attendance Management System"
    assert "irrigation" not in txt.lower()


def test_6_title_inside_table_cell():
    """Test 6: Title inside a table cell."""
    p = """<w:tbl xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
        <w:tr>
            <w:tc>
                <w:p>
                    <w:r><w:rPr><w:b/><w:sz w:val="36"/></w:rPr><w:t>AI Based Irrigation System</w:t></w:r>
                </w:p>
            </w:tc>
        </w:tr>
    </w:tbl>"""
    tpl = create_test_docx([p])
    out = os.path.join(tempfile.mkdtemp(), "out.docx")

    res = PackageLevelDocxEngine.replace(
        template_path=tpl,
        field_values={"project_title": "Ai based irrigation"},
        field_mapping=[{"arm_field": "project_title", "template_element": "AI Based Irrigation System", "action": "replace"}],
        output_path=out,
        job_id="test6",
    )
    assert res.success is True
    txt = read_doc_text(out)
    assert txt == "Ai based irrigation"


def test_7_isolation_to_first_page_only():
    """Test 7: Replace ONLY first-page title, do NOT replace occurrences on later pages."""
    p1 = """<w:p xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
        <w:r><w:rPr><w:b/><w:sz w:val="48"/></w:rPr><w:t>AI Based Irrigation System</w:t></w:r>
        <w:r><w:br w:type="page"/></w:r>
    </w:p>"""
    p2 = """<w:p xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
        <w:r><w:t>Overview of AI Based Irrigation System in agriculture.</w:t></w:r>
    </w:p>"""
    tpl = create_test_docx([p1, p2])
    out = os.path.join(tempfile.mkdtemp(), "out.docx")

    res = PackageLevelDocxEngine.replace(
        template_path=tpl,
        field_values={"project_title": "Ai based irrigation"},
        field_mapping=[{"arm_field": "project_title", "template_element": "AI Based Irrigation System", "action": "replace"}],
        output_path=out,
        job_id="test7",
    )
    assert res.success is True
    txt = read_doc_text(out)
    lines = txt.split("\n")
    assert lines[0] == "Ai based irrigation"
    assert lines[1] == "Overview of AI Based Irrigation System in agriculture."
