import xlwt
from StringIO import StringIO


def create_excel(name, fields, rows):
    style = xlwt.XFStyle()
    style.font = xlwt.Font()
    style.font.bold = True

    wb = xlwt.Workbook(encoding='utf8')
    sheet = wb.add_sheet(name)
    for idx, col_name in enumerate(fields):
        sheet.row(0).set_cell_text(idx, col_name, style)

    style.font.bold = False
    for row_idx, cells in enumerate(rows, 1):
        for col_idx, cell_value in enumerate(cells):
            sheet.row(row_idx).set_cell_text(col_idx, cell_value, style)

    output = StringIO()
    wb.save(output)
    return output.getvalue()
