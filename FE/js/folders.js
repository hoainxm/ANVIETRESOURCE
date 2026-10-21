import { bindLogoutButton, requireAuthentication } from "./services/apiClient.js";
import { createFolder, deleteFolder, getFolders } from "./services/recordsService.js";

const list = document.getElementById("folderList");
const status = document.getElementById("statusLine");
const dialog = document.getElementById("folderDialog");
const deleteDialog = document.getElementById("deleteFolderDialog");
const deleteDialogMessage = document.getElementById("deleteFolderMessage");
const nameInput = document.getElementById("folderName");
const error = document.getElementById("folderError");
const searchInput = document.getElementById("folderSearch");
const folderCount = document.getElementById("folderCount");
const MAX_FOLDERS = 100;
let folders = [];

function confirmFolderDeletion(folderName) {
  if (!deleteDialog?.showModal) {
    throw new Error("Trình duyệt không hỗ trợ hộp thoại xác nhận xóa.");
  }

  deleteDialogMessage.textContent =
    `Bạn có chắc muốn xóa thư mục "${folderName}" cùng toàn bộ hồ sơ bên trong không?`;
  const result = new Promise((resolve) => {
    deleteDialog.addEventListener(
      "close",
      () => resolve(deleteDialog.returnValue === "confirm"),
      { once: true },
    );
  });
  deleteDialog.showModal();
  return result;
}

function render() {
  const keyword = searchInput.value.trim().toLocaleLowerCase("vi");
  const filtered = folders.filter((folder) =>
    folder.name.toLocaleLowerCase("vi").includes(keyword),
  );
  list.replaceChildren();
  folderCount.textContent = `${folders.length}/${MAX_FOLDERS} thư mục`;
  document.getElementById("btnNewFolder").disabled = folders.length >= MAX_FOLDERS;

  if (!filtered.length) {
    list.textContent = folders.length
      ? "Không tìm thấy thư mục phù hợp."
      : "Chưa có thư mục. Hãy tạo thư mục mới.";
    return;
  }

  for (const folder of filtered) {
    const card = document.createElement("article");
    card.className = "folder-card";
    const title = document.createElement("h3");
    title.textContent = folder.name;
    const count = document.createElement("p");
    count.textContent = `${folder.profileCount} hồ sơ`;
    const open = document.createElement("a");
    open.className = "btn btn-primary";
    open.textContent = "Mở hồ sơ";
    open.href = `./profiles.html?folderId=${encodeURIComponent(folder.id)}`;
    const remove = document.createElement("button");
    remove.className = "folder-delete";
    remove.type = "button";
    remove.textContent = "×";
    remove.setAttribute("aria-label", `Xóa thư mục ${folder.name}`);
    remove.title = "Xóa thư mục";
    remove.addEventListener("click", async () => {
      if (!(await confirmFolderDeletion(folder.name))) return;
      remove.disabled = true;
      status.textContent = "";
      try {
        await deleteFolder(folder.id);
        status.textContent = `Đã xóa thư mục "${folder.name}".`;
        await loadFolders();
      } catch (requestError) {
        status.textContent = `Không thể xóa thư mục: ${requestError.message}`;
        remove.disabled = false;
      }
    });
    card.append(remove, title, count, open);
    list.appendChild(card);
  }
}

async function loadFolders() {
  list.textContent = "Đang tải thư mục...";
  try {
    folders = await getFolders();
    status.textContent = "";
    render();
  } catch (requestError) {
    list.textContent = `Không thể tải thư mục: ${requestError.message}`;
  }
}

document.getElementById("btnNewFolder").addEventListener("click", () => {
  error.textContent = "";
  nameInput.value = "";
  dialog.showModal();
  nameInput.focus();
});
document.getElementById("cancelFolder").addEventListener("click", () => dialog.close());
document.getElementById("saveFolder").addEventListener("click", async (event) => {
  event.preventDefault();
  const name = nameInput.value.trim();
  if (!name) {
    error.textContent = "Hãy nhập tên thư mục.";
    return;
  }
  const button = event.currentTarget;
  button.disabled = true;
  error.textContent = "";
  try {
    await createFolder(name);
    dialog.close();
    searchInput.value = "";
    await loadFolders();
  } catch (requestError) {
    error.textContent = requestError.message;
  } finally {
    button.disabled = false;
  }
});
searchInput.addEventListener("input", render);

try {
  const session = await requireAuthentication();
  if (session) {
    bindLogoutButton(document.getElementById("logoutButton"));
    document.getElementById("migrationLink").hidden = session.user.role !== "admin";
    await loadFolders();
  }
} catch (requestError) {
  list.textContent = `Không thể kết nối backend: ${requestError.message}`;
}
