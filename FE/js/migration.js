import { apiRequest, requireAuthentication } from "./services/apiClient.js";

const input = document.getElementById("backupFile");
const preview = document.getElementById("previewButton");
const commit = document.getElementById("importButton");
const result = document.getElementById("previewResult");
const errorElement = document.getElementById("migrationError");
let bundle = null;

try {
  const session = await requireAuthentication();
  if (!session || session.user.role !== "admin") {
    errorElement.textContent = "Chỉ quản trị viên mới được nhập dữ liệu.";
    preview.disabled = true;
    input.disabled = true;
  }
} catch (error) {
  errorElement.textContent = error.message;
  preview.disabled = true;
  input.disabled = true;
}

input.addEventListener("change", () => {
  bundle = null;
  commit.disabled = true;
  result.replaceChildren();
  errorElement.textContent = "";
});

preview.addEventListener("click", async () => {
  const file = input.files?.[0];
  bundle = null;
  commit.disabled = true;
  if (!file) {
    errorElement.textContent = "Hãy chọn tệp sao lưu.";
    return;
  }
  if (file.size > 25 * 1024 * 1024) {
    errorElement.textContent = "Tệp vượt giới hạn an toàn 25 MB. Hãy xuất/chia nhỏ dữ liệu trước khi nhập.";
    return;
  }
  preview.disabled = true;
  errorElement.textContent = "";
  try {
    const parsed = JSON.parse(await file.text());
    const response = await apiRequest("/api/admin/import/preview", {
      method: "POST",
      body: parsed,
    });
    const lines = [
      `Thư mục: ${response.folderCount}`,
      `Hồ sơ: ${response.profileCount}`,
      `Ảnh: ${response.imageCount}`,
      `Có thể nhập: ${response.canImport ? "Có" : "Không"}`,
      ...response.issues.map((issue) => `${issue.record} #${issue.index}: ${issue.message}`),
    ];
    result.replaceChildren(...lines.map((line) => {
      const paragraph = document.createElement("p");
      paragraph.textContent = line;
      return paragraph;
    }));
    if (response.canImport) {
      bundle = parsed;
      commit.disabled = false;
    }
  } catch (error) {
    errorElement.textContent = error.message;
  } finally {
    preview.disabled = false;
  }
});

commit.addEventListener("click", async () => {
  if (!bundle || !confirm("Nhập các hồ sơ đã xem trước? Dữ liệu nguồn trong browser sẽ không bị xóa.")) return;
  commit.disabled = true;
  try {
    const response = await apiRequest("/api/admin/import", { method: "POST", body: bundle });
    result.textContent = `Đã nhập ${response.folderCount} thư mục và ${response.profileCount} hồ sơ.`;
    bundle = null;
  } catch (error) {
    errorElement.textContent = error.message;
    commit.disabled = false;
  }
});
