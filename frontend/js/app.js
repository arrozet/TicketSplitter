// URLs de la API (ajustar si es necesario, por ejemplo, si FastAPI corre en un puerto diferente)
const API_BASE_URL = "http://localhost:8000/api/v1/receipts";

// Elementos del DOM
const receiptImageInput = document.getElementById('receiptImage');
const uploadButton = document.getElementById('uploadButton');
const uploadProgress = document.getElementById('uploadProgress');
const errorDisplay = document.getElementById('errorDisplay');
const fileNameDisplay = document.getElementById('fileNameDisplay'); // Para el nombre del archivo

const uploadBox = document.getElementById('uploadBox');
const parsedItemsBox = document.getElementById('parsedItemsBox');
const assignmentBox = document.getElementById('assignmentBox');
const splitResultsBox = document.getElementById('splitResultsBox');

const receiptIdDisplay = document.getElementById('receiptIdDisplay');
const rawTextDisplay = document.getElementById('rawText'); // El <pre> dentro del contenedor
const itemsTableBody = document.getElementById('itemsTableBody');
const subtotalDisplay = document.getElementById('subtotalDisplay');
const taxDisplay = document.getElementById('taxDisplay');
const totalDisplay = document.getElementById('totalDisplay');

const userNameInput = document.getElementById('userNameInput');
const addPersonButton = document.getElementById('addPersonButton');
const userAssignmentsDiv = document.getElementById('userAssignments');
const calculateSplitButton = document.getElementById('calculateSplitButton');

const resultsTableBody = document.getElementById('resultsTableBody');
const finalCalculatedTotalDisplay = document.getElementById('finalCalculatedTotalDisplay');

// Estado de la aplicación (variables globales para mantener el estado)
let currentReceiptId = null; // ID del recibo actualmente procesado
let parsedItems = []; // Lista de items parseados del recibo actual
let userItemSelections = {}; // Objeto para almacenar { "userName": [itemId1, itemId2, ...] }

// --- Funciones de Ayuda (Helpers) ---
function showError(message) {
    // Muestra un mensaje de error en el div designado
    errorDisplay.textContent = message;
    errorDisplay.classList.remove('is-hidden');
    console.error("Error displayed to user:", message); // También loguea en consola para depuración
}

function clearError() {
    // Oculta el mensaje de error
    errorDisplay.classList.add('is-hidden');
    errorDisplay.textContent = '';
}

function showProgress(isLoading = true) {
    // Muestra u oculta la barra de progreso y actualiza el estado del botón
    uploadProgress.classList.toggle('is-hidden', !isLoading);
    uploadButton.classList.toggle('is-loading', isLoading);
    calculateSplitButton.classList.toggle('is-loading', isLoading); // También para el botón de calcular
}

function formatCurrency(amount) {
    // Formatea un número como moneda (Euro)
    return amount !== null && amount !== undefined ? `${parseFloat(amount).toFixed(2)} €` : '-';
}

// --- Lógica de Carga y Parseo del Ticket ---
uploadButton.addEventListener('click', async () => {
    clearError();
    const file = receiptImageInput.files[0];
    if (!file) {
        showError("Please select an image file.");
        return;
    }

    const formData = new FormData();
    formData.append("file", file);

    showProgress(true);

    try {
        const response = await fetch(`${API_BASE_URL}/upload`, {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: "Unknown upload error." }));
            throw new Error(`Error ${response.status}: ${errorData.detail}`);
        }

        const data = await response.json();
        currentReceiptId = data.receipt_id;
        parsedItems = data.items || [];
        
        receiptIdDisplay.textContent = currentReceiptId;
        rawTextDisplay.textContent = data.raw_text || "(No text extracted or not available)";
        subtotalDisplay.textContent = formatCurrency(data.subtotal);
        taxDisplay.textContent = formatCurrency(data.tax);
        totalDisplay.textContent = formatCurrency(data.total);

        renderParsedItemsTable();
        resetUserAssignmentsUI(); // Limpiar asignaciones de UI de cualquier procesamiento anterior

        // Mostrar/ocultar secciones apropiadas de la UI
        uploadBox.classList.add('is-hidden');
        parsedItemsBox.classList.remove('is-hidden');
        assignmentBox.classList.remove('is-hidden');
        splitResultsBox.classList.add('is-hidden'); // Ocultar resultados anteriores

    } catch (error) {
        showError(error.message || "There was a problem processing the receipt.");
        // Si hay un error, es posible que queramos volver a mostrar el cuadro de carga
        uploadBox.classList.remove('is-hidden');
        parsedItemsBox.classList.add('is-hidden');
        assignmentBox.classList.add('is-hidden');
    } finally {
        showProgress(false);
    }
});

function renderParsedItemsTable() {
    // Renderiza la tabla de ítems parseados
    itemsTableBody.innerHTML = ''; // Limpiar tabla antes de rellenar
    if (parsedItems.length === 0) {
        itemsTableBody.innerHTML = '<tr><td colspan="5" class="has-text-centered">No items found in the receipt. You might need to verify the OCR text or the receipt image.</td></tr>';
        return;
    }
    parsedItems.forEach(item => {
        const row = itemsTableBody.insertRow();
        row.innerHTML = `
            <td>${item.id}</td>
            <td>${item.name}</td>
            <td>${item.quantity}</td>
            <td>${formatCurrency(item.price)}</td>
            <td>${formatCurrency(item.total_price)}</td>
        `;
    });
}

// --- Lógica de Asignación de Items a Personas ---
addPersonButton.addEventListener('click', () => {
    const userName = userNameInput.value.trim();
    if (!userName) {
        showError("Please enter a name for the person.");
        return;
    }
    if (userItemSelections.hasOwnProperty(userName)){
        showError(`Person '${userName}' has already been added.`);
        return;
    }
    clearError();
    userItemSelections[userName] = []; // Inicializa la lista de items para esta persona
    renderUserAssignmentBlockUI(userName);
    userNameInput.value = ''; // Limpiar input después de añadir
    userNameInput.focus(); // Poner foco de nuevo en el input
});

function renderUserAssignmentBlockUI(userName) {
    // Crea y añade el bloque de UI para que un usuario asigne items
    const userDiv = document.createElement('div');
    userDiv.className = 'user-block notification is-light p-4'; // Clases de Bulma para estilizar
    userDiv.dataset.userName = userName; // Guardar el nombre de usuario en el dataset para referencia

    const title = document.createElement('p');
    title.className = 'title is-5'; // Título más pequeño para el bloque de persona
    title.textContent = userName;
    userDiv.appendChild(title);

    const itemsChecklistDiv = document.createElement('div');
    itemsChecklistDiv.className = 'content';

    if (parsedItems.length === 0) {
        itemsChecklistDiv.innerHTML = '<p>No items available to assign.</p>';
    } else {
        parsedItems.forEach(item => {
            const field = document.createElement('div');
            field.className = 'field';
            
            const checkboxLabel = document.createElement('label');
            checkboxLabel.className = 'checkbox subtitle is-6'; // Estilo de checkbox de Bulma
            checkboxLabel.style.fontWeight = 'normal'; // Resetear strong del subtitle
            checkboxLabel.style.marginBottom = '0.5rem';
            checkboxLabel.style.display = 'block';

            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.value = item.id;
            checkbox.dataset.itemId = item.id;
            checkbox.style.marginRight = '8px';
            checkbox.addEventListener('change', (event) => {
                handleItemSelectionChange(userName, parseInt(event.target.value), event.target.checked);
            });

            checkboxLabel.appendChild(checkbox);
            checkboxLabel.appendChild(document.createTextNode(` ${item.id}: ${item.name} (${formatCurrency(item.total_price)})`));
            field.appendChild(checkboxLabel);
            itemsChecklistDiv.appendChild(field);
        });
    }
    userDiv.appendChild(itemsChecklistDiv);
    userAssignmentsDiv.appendChild(userDiv);
}

function handleItemSelectionChange(userName, itemId, isSelected) {
    // Actualiza el estado 'userItemSelections' cuando un checkbox cambia
    if (!userItemSelections[userName]) return; // Seguridad, aunque no debería pasar

    if (isSelected) {
        if (!userItemSelections[userName].includes(itemId)) {
            userItemSelections[userName].push(itemId);
        }
    } else {
        userItemSelections[userName] = userItemSelections[userName].filter(id => id !== itemId);
    }
    // console.log("Updated selections:", userItemSelections); // Para depuración
}

function resetUserAssignmentsUI() {
    // Limpia el estado de las selecciones y la UI de asignaciones
    userItemSelections = {};
    userAssignmentsDiv.innerHTML = '';
}

// --- Lógica de Cálculo de División ---
calculateSplitButton.addEventListener('click', async () => {
    if (!currentReceiptId) {
        showError("You need to upload and process a receipt first.");
        return;
    }

    // Prepara los datos de asignación para enviar a la API
    // Solo incluye usuarios que tengan al menos un ítem asignado
    const assignmentsPayload = Object.entries(userItemSelections)
        .filter(([_, itemIds]) => itemIds.length > 0)
        .reduce((obj, [key, value]) => {
            obj[key] = value;
            return obj;
        }, {});

    if (Object.keys(assignmentsPayload).length === 0) {
        showError("Please assign at least one item to a person, or add people to split common costs.");
        // Si queremos permitir la división equitativa de todo sin asignaciones explícitas,
        // esta lógica necesitaría cambiar. Por ahora, se requiere asignación o al menos un usuario añadido.
        // Para forzar división equitativa si no hay items asignados pero sí usuarios:
        if (Object.keys(userItemSelections).length > 0 && parsedItems.length > 0) {
            // Si hay usuarios pero ninguna asignación, llenar el payload con todos los usuarios y listas vacías de items
            // para que el backend divida todo equitativamente entre los listados.
            Object.keys(userItemSelections).forEach(name => {
                if (!assignmentsPayload[name]) assignmentsPayload[name] = [];
            });
        } else if (Object.keys(userItemSelections).length === 0 && parsedItems.length > 0) {
            showError("Please add people to assign items or to split common costs.");
            return;
        }
    }
    
    clearError();
    showProgress(true); // Mostrar progreso en el botón de calcular

    try {
        const response = await fetch(`${API_BASE_URL}/${currentReceiptId}/split`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ user_item_assignments: assignmentsPayload }),
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: "Unknown error during calculation." }));
            throw new Error(`Error ${response.status}: ${errorData.detail}`);
        }

        const results = await response.json();
        renderSplitResultsTable(results);
        splitResultsBox.classList.remove('is-hidden');

    } catch (error) {
        showError(error.message || "There was a problem calculating the split.");
    } finally {
        showProgress(false); // Ocultar progreso en el botón de calcular
    }
});

function renderSplitResultsTable(results) {
    // Renderiza la tabla con los resultados de la división
    resultsTableBody.innerHTML = ''; // Limpiar tabla anterior
    if (!results.shares || results.shares.length === 0) {
        resultsTableBody.innerHTML = '<tr><td colspan="3" class="has-text-centered">Could not calculate split or no results available.</td></tr>';
        finalCalculatedTotalDisplay.textContent = formatCurrency(0);
        return;
    }

    results.shares.forEach(share => {
        const row = resultsTableBody.insertRow();
        const assignedItemsNames = share.items.map(item => `${item.name} (${formatCurrency(item.total_price)})`).join(', <br>'); // <br> para saltos de línea si hay muchos items
        row.innerHTML = `
            <td><strong>${share.user_id}</strong></td>
            <td>${assignedItemsNames || '<em>Shared costs / Unassigned items</em>'}</td>
            <td class="has-text-weight-bold">${formatCurrency(share.amount_due)}</td>
        `;
    });
    finalCalculatedTotalDisplay.textContent = formatCurrency(results.total_calculated);
    // Scroll hacia los resultados para mejor UX
    splitResultsBox.scrollIntoView({ behavior: 'smooth' });
}

// Inicialización de la UI al cargar la página
function initUI() {
    // Ocultar secciones que no deben ser visibles al inicio
    parsedItemsBox.classList.add('is-hidden');
    assignmentBox.classList.add('is-hidden');
    splitResultsBox.classList.add('is-hidden');
    uploadProgress.classList.add('is-hidden'); // Asegurar que la barra de progreso esté oculta

    // Script para mostrar el nombre del archivo en el input de tipo file de Bulma
    // Este script ya está en index.html, pero lo mantenemos aquí por si se mueve a un solo bundle JS.
    // Si está duplicado, asegurarse que solo uno maneje el evento o que no interfieran.
    // Por ahora, el de index.html es suficiente y está bien localizado.
}

// Ejecutar inicialización
initUI(); 