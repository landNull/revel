/* Shared node edit + delete confirm. Every surface is a task node. */
(function (global) {
  var pendingDelete = null;
  var onSaved = null;
  var onDeleted = null;
  var ready = false;

  function nodeLabel(type) {
    return (type || "node").replace(/_/g, " ");
  }

  function ensureModals() {
    if (ready) return;
    if (!document.getElementById("editModal")) {
      document.body.insertAdjacentHTML("beforeend",
        '<div class="modal fade" id="editModal" tabindex="-1" aria-labelledby="editModalLabel" aria-hidden="true">' +
          '<div class="modal-dialog modal-dialog-scrollable">' +
            '<form class="modal-content" id="editForm">' +
              '<div class="modal-header">' +
                '<h2 class="modal-title h5" id="editModalLabel">Edit node</h2>' +
                '<button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>' +
              '</div>' +
              '<div class="modal-body">' +
                '<input type="hidden" id="edit-id">' +
                '<input type="hidden" id="edit-type">' +
                '<div class="mb-2">' +
                  '<label class="form-label" for="edit-title">title</label>' +
                  '<input class="form-control form-control-sm" id="edit-title" required>' +
                '</div>' +
                '<div class="mb-2">' +
                  '<label class="form-label" for="edit-column">column</label>' +
                  '<select class="form-select form-select-sm" id="edit-column">' +
                    '<option value="todo">todo</option>' +
                    '<option value="doing">doing</option>' +
                    '<option value="done">done</option>' +
                  '</select>' +
                '</div>' +
                '<div class="row g-2 mb-2">' +
                  '<div class="col">' +
                    '<label class="form-label" for="edit-start">start</label>' +
                    '<input class="form-control form-control-sm" id="edit-start" type="date">' +
                  '</div>' +
                  '<div class="col">' +
                    '<label class="form-label" for="edit-end">end</label>' +
                    '<input class="form-control form-control-sm" id="edit-end" type="date">' +
                  '</div>' +
                '</div>' +
                '<div class="mb-0">' +
                  '<label class="form-label" for="edit-due">due</label>' +
                  '<input class="form-control form-control-sm" id="edit-due" type="date">' +
                '</div>' +
              '</div>' +
              '<div class="modal-footer justify-content-between">' +
                '<button type="button" class="btn" id="edit-delete">Delete</button>' +
                '<button type="submit" class="btn btn-primary">Save</button>' +
              '</div>' +
            '</form>' +
          '</div>' +
        '</div>'
      );
    }
    if (!document.getElementById("deleteModal")) {
      document.body.insertAdjacentHTML("beforeend",
        '<div class="modal fade revel-confirm" id="deleteModal" tabindex="-1" aria-labelledby="deleteModalLabel" aria-hidden="true">' +
          '<div class="modal-dialog modal-dialog-centered">' +
            '<div class="modal-content">' +
              '<div class="modal-header">' +
                '<h2 class="modal-title h5" id="deleteModalLabel">Delete node</h2>' +
                '<button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>' +
              '</div>' +
              '<div class="modal-body">' +
                '<p class="mb-0" id="delete-message">Are you sure you want to delete this node?</p>' +
              '</div>' +
              '<div class="modal-footer">' +
                '<button type="button" class="btn btn-outline-secondary" data-bs-dismiss="modal">Cancel</button>' +
                '<button type="button" class="btn" id="delete-confirm">Delete</button>' +
              '</div>' +
            '</div>' +
          '</div>' +
        '</div>'
      );
    }
    bindOnce();
    ready = true;
  }

  function bindOnce() {
    var form = document.getElementById("editForm");
    if (form && !form.dataset.revelBound) {
      form.dataset.revelBound = "1";
      form.addEventListener("submit", function (ev) {
        ev.preventDefault();
        saveEdit();
      });
    }
    var delBtn = document.getElementById("edit-delete");
    if (delBtn && !delBtn.dataset.revelBound) {
      delBtn.dataset.revelBound = "1";
      delBtn.addEventListener("click", function () {
        var id = document.getElementById("edit-id").value;
        var type = document.getElementById("edit-type").value;
        var title = document.getElementById("edit-title").value;
        openDelete({id: id, type: type, title: title}, onDeleted);
      });
    }
    var confirmBtn = document.getElementById("delete-confirm");
    if (confirmBtn && !confirmBtn.dataset.revelBound) {
      confirmBtn.dataset.revelBound = "1";
      confirmBtn.addEventListener("click", confirmDelete);
    }
  }

  async function mutate(id, body) {
    var res = await fetch("/nodes/" + id, {
      method: "PATCH",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(body)
    });
    if (!res.ok) throw new Error("mutate failed");
    return res.json();
  }

  async function openEdit(id, savedCb) {
    ensureModals();
    onSaved = savedCb || null;
    onDeleted = savedCb || onDeleted;
    var node = await (await fetch("/nodes/" + id)).json();
    document.getElementById("edit-id").value = node.id;
    document.getElementById("edit-type").value = node.type;
    document.getElementById("edit-title").value = node.title;
    document.getElementById("edit-column").value = node.payload.column || "todo";
    document.getElementById("edit-start").value = node.payload.start || "";
    document.getElementById("edit-end").value = node.payload.end || "";
    document.getElementById("edit-due").value = node.payload.due || "";
    document.getElementById("editModalLabel").textContent = "Edit " + nodeLabel(node.type);
    bootstrap.Modal.getOrCreateInstance(document.getElementById("editModal")).show();
  }

  function openDelete(node, deletedCb) {
    ensureModals();
    onDeleted = deletedCb || onDeleted;
    pendingDelete = {
      id: node.id,
      type: node.type || "node",
      title: node.title || ""
    };
    var msg = "Are you sure you want to delete this " + nodeLabel(pendingDelete.type) + "?";
    document.getElementById("delete-message").textContent = msg;
    document.getElementById("deleteModalLabel").textContent = "Delete " + nodeLabel(pendingDelete.type);
    bootstrap.Modal.getOrCreateInstance(document.getElementById("deleteModal")).show();
  }

  async function saveEdit() {
    var id = document.getElementById("edit-id").value;
    await mutate(id, {
      title: document.getElementById("edit-title").value,
      payload: {
        column: document.getElementById("edit-column").value,
        start: document.getElementById("edit-start").value,
        end: document.getElementById("edit-end").value,
        due: document.getElementById("edit-due").value
      }
    });
    bootstrap.Modal.getInstance(document.getElementById("editModal")).hide();
    if (onSaved) onSaved(id);
  }

  async function confirmDelete() {
    if (!pendingDelete) return;
    var res = await fetch("/nodes/" + pendingDelete.id, {method: "DELETE"});
    if (!res.ok) return;
    var id = pendingDelete.id;
    pendingDelete = null;
    var delModal = bootstrap.Modal.getInstance(document.getElementById("deleteModal"));
    var editModal = bootstrap.Modal.getInstance(document.getElementById("editModal"));
    if (delModal) delModal.hide();
    if (editModal) editModal.hide();
    if (onDeleted) onDeleted(id);
  }

  function boot() {
    ensureModals();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }

  global.RevelNode = {
    mutate: mutate,
    openEdit: openEdit,
    openDelete: openDelete
  };
})(window);
