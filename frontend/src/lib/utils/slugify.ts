/**
 * Slugify tiếng Việt → ascii lowercase hyphen.
 *
 * Convenience cho FE auto-fill slug field. BE (python-slugify) là source
 * of truth — nếu FE gửi slug rỗng, BE tự generate. Hàm này chỉ để preview
 * tức thì cho user, không cần khớp 100% python-slugify.
 */
export function slugify(input: string): string {
  return input
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "") // bỏ dấu (combining diacritics)
    .replace(/đ/g, "d")
    .replace(/Đ/g, "D")
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "-") // non-alphanumeric → hyphen
    .replace(/^-+|-+$/g, ""); // trim hyphen đầu/cuối
}
