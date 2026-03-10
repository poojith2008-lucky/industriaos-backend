import qrcode
import os
import json
from datetime import datetime
from app.core.config import settings


def generate_payroll_qr(
    employee_name: str,
    employee_id: int,
    month: int,
    year: int,
    net_salary: float,
    payroll_id: int,
) -> str:
    data = {
        "type": "SALARY_PAYMENT",
        "payroll_id": payroll_id,
        "employee_id": employee_id,
        "employee_name": employee_name,
        "amount": net_salary,
        "month": month,
        "year": year,
        "generated_at": datetime.utcnow().isoformat(),
    }

    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(json.dumps(data))
    qr.make(fit=True)

    img = qr.make_image(fill_color="#080B14", back_color="white")

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    filename = f"qr_payroll_{payroll_id}_{employee_id}_{month}_{year}.png"
    filepath = os.path.join(settings.UPLOAD_DIR, filename)
    img.save(filepath)

    return filepath