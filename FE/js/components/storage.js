import { apiRequest } from "../services/apiClient.js";

function currentFolderId() {
  const folderId = new URLSearchParams(window.location.search).get("folderId");
  if (!folderId) throw new Error("Thiếu mã thư mục. Hãy quay lại chọn thư mục.");
  return folderId;
}

function normalizeProfileAddress(profile) {
  const normalized = { ...profile };
  const soNha = String(normalized.soNhaHienNay ?? "").trim();
  const phuongXa = String(normalized.phuongXaHienNay ?? "").trim();
  const quanHuyen = String(normalized.quanHuyenHienNay ?? "").trim();
  const tinh = String(normalized.tinhHienNay ?? "").trim();
  normalized.diaChiHienNay = [soNha, phuongXa, quanHuyen, tinh]
    .filter(
      (value) =>
        value && value.toLocaleLowerCase("vi") !== "không áp dụng",
    )
    .join(", ");
  return normalized;
}

export async function saveProfile(profile) {
  const normalized = normalizeProfileAddress(profile);
  if (normalized.version) {
    const response = await apiRequest(`/api/profiles/${encodeURIComponent(normalized.id)}`, {
      method: "PATCH",
      headers: { "If-Match": String(normalized.version) },
      body: normalized,
    });
    return response.profile;
  }
  const response = await apiRequest(
    `/api/folders/${encodeURIComponent(currentFolderId())}/profiles`,
    { method: "POST", body: normalized },
  );
  return response.profile;
}

export async function getProfileById(id) {
  const response = await apiRequest(`/api/profiles/${encodeURIComponent(id)}`);
  return response.profile;
}
