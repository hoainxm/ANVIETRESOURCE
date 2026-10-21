import { apiRequest } from "./apiClient.js";

export async function getFolders() {
  const response = await apiRequest("/api/folders");
  return response.folders;
}

export async function createFolder(name) {
  return apiRequest("/api/folders", { method: "POST", body: { name } });
}

export async function deleteFolder(id) {
  return apiRequest(`/api/folders/${encodeURIComponent(id)}`, { method: "DELETE" });
}

export async function getFolder(id) {
  const response = await apiRequest(`/api/folders/${encodeURIComponent(id)}`);
  return response.folder;
}

export async function getProfilesInFolder(id) {
  const response = await apiRequest(`/api/folders/${encodeURIComponent(id)}/profiles`);
  return response.profiles;
}

export async function deleteFolderProfiles(folderId, ids) {
  return apiRequest(
    `/api/folders/${encodeURIComponent(folderId)}/profiles/delete`,
    { method: "POST", body: { ids: ids.map(String) } },
  );
}
