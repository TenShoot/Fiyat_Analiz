import hashlib

SECRET_SALT = "TenShoot-2026"  # fiyat.py ile AYNI OLMALI

PLATFORMS = {
    "1": ("Windows", "license.ten"),
    "2": ("Mac",     "license_mac.ten"),
}


def main():
    machine_id = input("Müşterinin Makine ID'sini gir: ").strip().upper()
    if not machine_id:
        print("Makine ID boş olamaz.")
        return

    print("\nPlatform seç:")
    for k, (label, fname) in PLATFORMS.items():
        print(f"  {k} - {label} ({fname})")
    choice = input("Seçim (1/2): ").strip()

    if choice not in PLATFORMS:
        print("Geçersiz seçim.")
        return

    label, fname = PLATFORMS[choice]

    license_key = hashlib.sha256(
        (machine_id + SECRET_SALT).encode("utf-8")
    ).hexdigest()

    print(f"\nÜretilen lisans anahtarı ({label}):")
    print(license_key)

    with open(fname, "w", encoding="utf-8") as f:
        f.write(license_key)

    print(f"\n{fname} dosyası oluşturuldu. Bunu müşteriye gönder.")


if __name__ == "__main__":
    main()
