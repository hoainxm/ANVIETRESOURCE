import { requireAuthentication } from "./services/apiClient.js";

function readList(key) {
  const raw = localStorage.getItem(key);
  if (!raw) return [];
  const value = JSON.parse(raw);
  if (!Array.isArray(value)) throw new Error(`Dữ liệu ${key} không phải danh sách.`);
  return value;
}

function readIndexedProfiles() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open("anviet_profiles");
    request.onerror = () => reject(request.error || new Error("Không mở được IndexedDB."));
    request.onsuccess = () => {
      const database = request.result;
      if (!database.objectStoreNames.contains("profiles")) {
        database.close();
        resolve([]);
        return;
      }
      const tx = database.transaction("profiles", "readonly");
      const query = tx.objectStore("profiles").getAll();
      query.onsuccess = () => resolve(query.result);
      query.onerror = () => reject(query.error || new Error("Không đọc được hồ sơ IndexedDB."));
      tx.oncomplete = () => database.close();
      tx.onerror = () => reject(tx.error || new Error("Lỗi đọc IndexedDB."));
    };
  });
}

const button = document.getElementById("exportButton");
const status = document.getElementById("exportStatus");
try {
  const session = await requireAuthentication();
  if (session) {
    button.addEventListener("click", async () => {
      button.disabled = true;
      try {
        const folders = readList("anviet_folders");
        const profiles = [
          ...readList("ho_so_list"),
          ...await readIndexedProfiles(),
        ];
        const unique = new Map();
        for (const profile of profiles) {
          if (!profile || profile.id === undefined || profile.id === null) {
            throw new Error("Có hồ sơ thiếu mã định danh; dừng để tránh nhập trùng.");
          }
          unique.set(String(profile.id), profile);
        }
        const records = [...unique.values()];
        let folderList = folders;
        if (!folderList.length && records.length) {
          folderList = [{ id: crypto.randomUUID(), name: "Dữ liệu chuyển từ browser" }];
          records.forEach((profile) => { profile.folderId ||= folderList[0].id; });
        }
        if (folderList.length === 1) {
          records.forEach((profile) => { profile.folderId ||= folderList[0].id; });
        }
        const blob = new Blob(
          [JSON.stringify({ version: 1, exportedAt: new Date().toISOString(), folders: folderList, profiles: records })],
          { type: "application/json" },
        );
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = `cmnd-backup-${new Date().toISOString().slice(0, 10)}.json`;
        link.click();
        setTimeout(() => URL.revokeObjectURL(url), 30000);
        status.textContent = `Đã sao lưu ${folderList.length} thư mục và ${records.length} hồ sơ. Dữ liệu nguồn vẫn được giữ nguyên.`;
      } catch (error) {
        status.textContent = `Không thể tạo bản sao lưu: ${error.message}`;
      } finally {
        button.disabled = false;
      }
    });
  }
} catch (error) {
  status.textContent = `Không thể kết nối: ${error.message}`;
  button.disabled = true;
}
