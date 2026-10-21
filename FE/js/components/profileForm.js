const form = () => document.getElementById("profileForm");

function fullAddress(parts) {
  return parts
    .map((value) => String(value ?? "").trim())
    .filter(
      (value) =>
        value && value.toLocaleLowerCase("vi") !== "không áp dụng",
    )
    .join(", ");
}

function combinePlaceValues(...values) {
  return values
    .map((value) => String(value ?? "").trim())
    .filter(
      (value, index, all) =>
        value &&
        all.findIndex(
          (item) => item.toLocaleLowerCase("vi") === value.toLocaleLowerCase("vi"),
        ) === index,
    )
    .join(" / ");
}

// ============================================================
// ĐỒNG BỘ ĐỊA CHỈ ĐẦY ĐỦ
// ============================================================

function rebuildAddressField(suffix) {
  const soNha = document.querySelector(`[name="soNha${suffix}"]`);
  const phuongXa = document.querySelector(`[name="phuongXa${suffix}"]`);
  const quanHuyen = document.querySelector(`[name="quanHuyen${suffix}"]`);
  const tinh = document.querySelector(
    `[name="${suffix === "HKTT" ? "HKTT_Tinh" : "tinhHienNay"}"]`,
  );
  const diaChi = document.querySelector(`[name="diaChi${suffix}"]`);

  if (!diaChi) return;

  // Luôn tạo lại từ các trường thành phần, không nối vào giá trị cũ.
  diaChi.value = fullAddress([
    soNha?.value,
    phuongXa?.value,
    quanHuyen?.value,
    tinh?.value,
  ]);
}

function syncAddress(suffix) {
  const soNha = document.querySelector(`[name="soNha${suffix}"]`);
  const phuongXa = document.querySelector(`[name="phuongXa${suffix}"]`);
  const quanHuyen = document.querySelector(`[name="quanHuyen${suffix}"]`);
  const tinh = document.querySelector(
    `[name="${suffix === "HKTT" ? "HKTT_Tinh" : "tinhHienNay"}"]`,
  );

  const rebuild = () => rebuildAddressField(suffix);

  [soNha, phuongXa, quanHuyen, tinh].forEach((field) => {
    if (!field || field.dataset.addressSyncBound === "true") return;

    field.addEventListener("input", rebuild);
    field.addEventListener("change", rebuild);
    field.dataset.addressSyncBound = "true";
  });

  rebuild();
}

// ============================================================
// KHỞI TẠO FORM
// ============================================================

export function initProfileForm() {
  const profileForm = form();
  if (!profileForm) {
    console.warn("Không tìm thấy #profileForm.");
    return;
  }

  // Thu gọn / mở rộng các phần thông tin.
  document.querySelectorAll(".form-section-title").forEach((title) => {
    if (title.dataset.sectionBound === "true") return;

    title.addEventListener("click", () => {
      const targetId = title.dataset.target;
      if (!targetId) return;

      const section = document.getElementById(targetId);
      if (!section) return;

      section.classList.toggle("hidden");
      title.classList.toggle("collapsed");
    });

    title.dataset.sectionBound = "true";
  });

  // Tự ghép họ và tên.
  const hoDem = profileForm.querySelector('[name="hoDem"]');
  const ten = profileForm.querySelector('[name="ten"]');
  const hoTen = profileForm.querySelector('[name="hoTen"]');

  const rebuildFullName = () => {
    if (!hoTen) return;

    hoTen.value = [hoDem?.value, ten?.value]
      .map((value) => String(value ?? "").trim())
      .filter(Boolean)
      .join(" ");
  };

  [hoDem, ten].forEach((field) => {
    if (!field || field.dataset.fullNameBound === "true") return;

    field.addEventListener("input", rebuildFullName);
    field.dataset.fullNameBound = "true";
  });

  // Đồng bộ hai nhóm địa chỉ.
  syncAddress("HKTT");
  syncAddress("HienNay");

  // Khởi tạo các combobox.
  [
    "gioiTinh",
    "danToc",
    "loaiGiayTo",
    "noiCapGiayTo",
  ].forEach((name) => {
    const input = profileForm.querySelector(`[name="${name}"]`);
    if (input) initCombobox(input);
  });
}

// ============================================================
// LẤY DỮ LIỆU FORM
// ============================================================

export function getFormData() {
  const profileForm = form();
  if (!profileForm) return {};

  const data = {};

  new FormData(profileForm).forEach((value, key) => {
    data[key] = value;
  });

  // Luôn lưu địa chỉ đầy đủ được ghép từ ba trường thành phần.
  data.diaChiHKTT = fullAddress([
    data.soNhaHKTT,
    data.phuongXaHKTT,
    data.quanHuyenHKTT,
    data.HKTT_Tinh,
  ]);

  data.diaChiHienNay = fullAddress([
    data.soNhaHienNay,
    data.phuongXaHienNay,
    data.quanHuyenHienNay,
    data.tinhHienNay,
  ]);

  return data;
}

// ============================================================
// ĐIỀN DỮ LIỆU VÀO FORM
// ============================================================

export function setFormData(data = {}) {
  const profileForm = form();
  if (!profileForm) return;

  Object.entries(data).forEach(([key, value]) => {
    const field = profileForm.querySelector(`[name="${key}"]`);
    if (!field) return;

    field.value = value ?? "";
  });

  const placeField = profileForm.querySelector('[name="noiSinhNguyenQuan"]');
  if (placeField) {
    placeField.value = combinePlaceValues(
      data.noiSinhNguyenQuan,
      data.noiSinh,
      data.nguyenQuan,
    );
  }

  // Nếu thiếu họ tên đầy đủ, tạo lại từ họ đệm và tên.
  const hoTen = profileForm.querySelector('[name="hoTen"]');

  if (hoTen && !String(hoTen.value ?? "").trim()) {
    const hoDem = profileForm.querySelector('[name="hoDem"]')?.value;
    const ten = profileForm.querySelector('[name="ten"]')?.value;

    hoTen.value = [hoDem, ten]
      .map((value) => String(value ?? "").trim())
      .filter(Boolean)
      .join(" ");
  }

  // Không giữ lại giá trị địa chỉ đầy đủ cũ nếu nó không khớp
  // với các trường thành phần hiện tại.
  rebuildAddressField("HKTT");
  rebuildAddressField("HienNay");
}

// ============================================================
// RESET FORM
// ============================================================

export function resetFormData() {
  const profileForm = form();
  if (!profileForm) return;

  profileForm.reset();

  profileForm
    .querySelectorAll(".combobox-options")
    .forEach((options) => {
      options.classList.remove("show", "hidden");
    });

  profileForm.querySelectorAll(".combobox").forEach((combobox) => {
    combobox.classList.remove("active");
  });

  rebuildAddressField("HKTT");
  rebuildAddressField("HienNay");
}

// ============================================================
// COMBOBOX
// ============================================================

function initCombobox(input) {
  if (!input || input.dataset.comboboxBound === "true") return;

  const wrapper = input.closest(".combobox");
  if (!wrapper) return;

  const options = wrapper.querySelector(".combobox-options");
  if (!options) return;

  const arrow = wrapper.querySelector(".combobox-arrow");
  const normalize = (value) =>
    String(value || "")
      .toLocaleLowerCase("vi")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/đ/g, "d")
      .trim();
  let activeIndex = -1;
  let noResult = options.querySelector(".combobox-no-result");

  const items = () =>
    Array.from(options.querySelectorAll(".combobox-option")).filter(
      (item) => !item.classList.contains("hidden"),
    );

  const closeOptions = () => {
    options.classList.remove("show");
    options.classList.add("hidden");
    wrapper.classList.remove("active");
    input.setAttribute("aria-expanded", "false");
    activeIndex = -1;
    options.querySelectorAll(".is-keyboard-active").forEach((item) => {
      item.classList.remove("is-keyboard-active");
    });
  };

  const openOptions = () => {
    options.classList.remove("hidden");
    options.classList.add("show");
    wrapper.classList.add("active");
    input.setAttribute("aria-expanded", "true");
  };

  const filterOptions = () => {
    const keyword = normalize(input.value).replace(/\s+/g, "");

    const optionItems = options.querySelectorAll(".combobox-option");
    let visibleCount = 0;
    optionItems.forEach((item) => {
      const text = normalize(item.textContent).replace(/\s+/g, "");
      const isVisible = !keyword || text.includes(keyword);
      item.classList.toggle("hidden", !isVisible);
      item.classList.remove("is-keyboard-active");
      if (isVisible) visibleCount += 1;
    });

    if (!noResult) {
      noResult = document.createElement("div");
      noResult.className = "combobox-no-result";
      noResult.textContent = "Không tìm thấy kết quả";
      options.append(noResult);
    }
    noResult.classList.toggle("hidden", visibleCount > 0);
    activeIndex = -1;
    openOptions();
  };

  const showAllOptions = () => {
    options.querySelectorAll(".combobox-option").forEach((item) => {
      item.classList.remove("hidden");
    });
    noResult?.classList.add("hidden");
    options.querySelectorAll(".is-keyboard-active").forEach((item) => {
      item.classList.remove("is-keyboard-active");
    });
    activeIndex = -1;
    openOptions();
  };

  input.addEventListener("focus", showAllOptions);
  input.addEventListener("click", showAllOptions);
  input.addEventListener("input", filterOptions);

  input.addEventListener("keydown", (event) => {
    const visibleItems = items();

    if (event.key === "Escape") {
      closeOptions();
      return;
    }

    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      openOptions();
      if (visibleItems.length) {
        const direction = event.key === "ArrowDown" ? 1 : -1;
        activeIndex =
          activeIndex < 0
            ? direction > 0
              ? 0
              : visibleItems.length - 1
            : (activeIndex + direction + visibleItems.length) %
              visibleItems.length;
        visibleItems.forEach((item, index) => {
          item.classList.toggle("is-keyboard-active", index === activeIndex);
        });
        visibleItems[activeIndex].scrollIntoView({ block: "nearest" });
      }
      return;
    }

    if (event.key === "Enter" && activeIndex >= 0) {
      event.preventDefault();
      items()[activeIndex]?.click();
    }
  });

  options.addEventListener("click", (event) => {
    const item = event.target.closest(".combobox-option");

    if (!item || !options.contains(item)) return;

    const value = item.dataset.value ?? item.textContent?.trim();

    if (value == null) return;

    input.value = String(value).trim();
    options.querySelectorAll(".combobox-option").forEach((option) => {
      option.classList.toggle("active", option === item);
      option.classList.remove("is-keyboard-active");
    });
    input.dispatchEvent(new Event("change", { bubbles: true }));
    closeOptions();
  });

  arrow?.addEventListener("click", (event) => {
    event.preventDefault();
    event.stopPropagation();
    if (options.classList.contains("show")) {
      closeOptions();
    } else {
      showAllOptions();
      input.focus();
    }
  });

  document.addEventListener("click", (event) => {
    if (!wrapper.contains(event.target)) {
      closeOptions();
    }
  });

  options.setAttribute("role", "listbox");
  input.setAttribute("aria-haspopup", "listbox");
  input.setAttribute("aria-expanded", "false");
  options.querySelectorAll(".combobox-option").forEach((item) => {
    item.setAttribute("role", "option");
  });
  input.dataset.comboboxBound = "true";
}
