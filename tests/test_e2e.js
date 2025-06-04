import { browser } from 'k6/browser';
import { check } from 'https://jslib.k6.io/k6-utils/1.5.0/index.js';
import { sleep } from 'k6';
import { open } from 'k6/experimental/fs';
import encoding from 'k6/encoding';

console.log("SCRIPT_LOG: Contexto de inicialización comenzando.");

// Función para leer el contenido de un archivo ya abierto y luego cerrarlo
async function readOpenedFileContent(fileHandle) {
  if (!fileHandle) {
    console.error("SCRIPT_LOG_ERROR: readOpenedFileContent fue llamado con un fileHandle nulo.");
    throw new Error("El manejador de archivo es nulo. El archivo no se pudo abrir en el contexto de inicialización.");
  }
  try {
    console.log("SCRIPT_LOG: Leyendo estadísticas del archivo...");
    const fileInfo = await fileHandle.stat();
    console.log(`SCRIPT_LOG: Estadísticas obtenidas: tamaño ${fileInfo.size}`);
    const buffer = new Uint8Array(fileInfo.size);
    console.log("SCRIPT_LOG: Leyendo contenido del archivo...");
    const bytesRead = await fileHandle.read(buffer);
    console.log(`SCRIPT_LOG: Bytes leídos: ${bytesRead}`);
    if (bytesRead !== fileInfo.size) {
      throw new Error(`Error al leer el archivo: se leyeron ${bytesRead} bytes de ${fileInfo.size}`);
    }
    return buffer.buffer; // Devuelve el ArrayBuffer subyacente
  } catch (e) {
    console.error(`SCRIPT_LOG_ERROR: Error en readOpenedFileContent: ${e.name} - ${e.message}`);
    throw e; // Relanzar el error para que sea visible
  } finally {
    if (fileHandle && typeof fileHandle.close === 'function') {
      try {
        console.log("SCRIPT_LOG: Intentando cerrar el archivo...");
        await fileHandle.close(); // Cerrar el archivo después de leerlo o en caso de error previo
        console.log("SCRIPT_LOG: Archivo cerrado exitosamente.");
      } catch (closeError) {
        console.error(`SCRIPT_LOG_ERROR: Error al cerrar el archivo: ${closeError.name} - ${closeError.message}`);
      }
    }
  }
}

// Abrir el archivo en el contexto de inicialización.
// Usamos una ruta absoluta para asegurar que k6 pueda encontrarlo.
const restauranteFilePath = 'D:/UMA/UMA_CODE/3/2cuatri/MPS/TicketSplitter/tests/images/restaurante.jpg';
let restauranteFilePromise = null;

console.log("SCRIPT_LOG: Configurando la promesa para abrir el archivo en el contexto de inicialización...");
try {
  restauranteFilePromise = (async () => {
    console.log(`SCRIPT_LOG: IIAFE iniciada para ${restauranteFilePath}.`);
    try {
      console.log(`SCRIPT_LOG: Intentando llamar a open() para ${restauranteFilePath}`);
      const file = await open(restauranteFilePath, 'r');
      console.log(`SCRIPT_LOG: open() exitoso para ${restauranteFilePath}. File object: ${typeof file}`);
      return file;
    } catch (e) {
      console.error(`SCRIPT_LOG_ERROR: IIAFE catch: Error en open() para ${restauranteFilePath}. Tipo: ${e.name}, Msg: ${e.message}`);
      console.error(`SCRIPT_LOG_ERROR_STACK: ${e.stack || 'No stack available'}`);
      return null;
    }
  })();
  console.log("SCRIPT_LOG: Promesa para open() configurada exitosamente.");
} catch (syncError) {
  console.error(`SCRIPT_LOG_ERROR: Error síncrono durante la configuración de la IIAFE: ${syncError.name} - ${syncError.message}`);
  restauranteFilePromise = Promise.resolve(null);
}

// Configuración de opciones
export const options = {
    scenarios: {
        browser: {
            executor: 'shared-iterations',
            vus: 1,
            iterations: 1,
            options: {
                browser: {
                    type: 'chromium',
                    headless: false
                }
            }
        }
    },
    thresholds: {
        http_req_duration: ['p(95)<500'], // 95% de las peticiones deben completarse en menos de 500ms
        http_req_failed: ['rate<0.01'], // Menos del 1% de las peticiones pueden fallar
    },
};

// Función principal de prueba
export default async function () {
    const page = await browser.newPage();
    try {
        // Navegar a la página principal
        await page.goto('http://localhost:4321');
        sleep(2);

        // Esperar a que el área de drop esté presente
        console.log('Esperando a que el área de drop esté presente...');
        await page.waitForSelector('.border-dashed');
        sleep(1);

        // Buscar el input de archivo por id
        console.log('Buscando input de archivo por id...');
        let fileInput = await page.$('#receipt-image');
        if (!fileInput) {
            console.log('No se encontró el input con id receipt-image. Buscando todos los inputs file...');
            // Imprimir todos los inputs file del DOM
            const allInputs = await page.evaluate(() => {
                return Array.from(document.querySelectorAll('input[type="file"]')).map(i => ({
                    id: i.id,
                    class: i.className,
                    name: i.name
                }));
            });
            console.log('Inputs file encontrados:', JSON.stringify(allInputs));
            throw new Error('No se encontró el input de archivo');
        }

        // Establecer el valor del input directamente usando setInputFiles
        console.log('Estableciendo el valor del input con setInputFiles para restaurante.jpg...');
        
        const restauranteFile = await restauranteFilePromise; // Esperar a que la promesa del archivo se resuelva
        if (!restauranteFile) {
            throw new Error(`No se pudo obtener el manejador para el archivo ${restauranteFilePath}. Revisa los logs del init context.`);
        }

        const restauranteBuffer = await readOpenedFileContent(restauranteFile);
        
        await fileInput.setInputFiles({
            name: 'restaurante.jpg',
            mimetype: 'image/jpeg',
            buffer: encoding.b64encode(restauranteBuffer),
        });
        
        console.log('Archivo seleccionado. Esperando 5 segundos para que la UI procese la imagen...');
        sleep(5); // Pausa generosa para que la UI se actualice después de la subida de la imagen

        // Buscar el botón "Subir y procesar"
        console.log('Buscando el botón "Subir y procesar"...');
        const allButtons = await page.$$('button');
        let subirBtnHandle = null;
        for (const btnHandle of allButtons) {
            const text = await btnHandle.textContent();
            if (text && text.includes('Subir y procesar')) {
                subirBtnHandle = btnHandle;
                break;
            }
        }

        if (!subirBtnHandle) { 
            console.error('CRITICAL: No se encontró el botón "Subir y procesar" tras iterar todos los botones.');
            await page.screenshot({ path: 'debug_no_subir_btn.png' });
            throw new Error('No se encontró el botón "Subir y procesar"');
        }
        
        console.log('Botón "Subir y procesar" encontrado. Intentando hacer clic...');
        try {
            await subirBtnHandle.click({ force: true, timeout: 10000 }); 
            console.log('Botón "Subir y procesar" clicado exitosamente (con force=true).');
        } catch (clickError) {
            console.warn(`Primer intento de clic (con force=true) falló: ${clickError.message}. Reintentando tras una breve pausa...`);
            await page.screenshot({ path: 'debug_primer_clic_forzado_fallido.png' });
        sleep(2);
            try {
                await subirBtnHandle.scrollIntoViewIfNeeded(); 
                await subirBtnHandle.click({ force: true, timeout: 10000 });
                console.log('Botón "Subir y procesar" clicado exitosamente en el segundo intento (con force=true).');
            } catch (secondClickError) {
                console.error(`ERROR CRÍTICO al hacer clic en el botón "Subir y procesar" en el segundo intento (con force=true): ${secondClickError.message}`);
                console.error(`Stack del error de clic (segundo intento, forzado): ${secondClickError.stack || 'No stack available'}`);
                await page.screenshot({ path: 'debug_segundo_clic_forzado_fallido.png' });
                throw secondClickError; 
            }
        }
        
        console.log('Esperando 3 segundos después del clic para la carga del Paso 2: Revisión de artículos...');
        sleep(3); 

        // --- VERIFICACIONES DEL PASO 2 (MOVIDAS AQUÍ) ---
        console.log('Realizando verificaciones del Paso 2: Revisión de artículos...');
        const bodyPaso2 = await page.locator('body');
        const contenidoPaso2 = await bodyPaso2.textContent();

        await check(bodyPaso2, {
            'P2: ticket restaurante procesado': () => { // Check síncrono ya que contenidoPaso2 ya está resuelto
                const expectedItems = ['AGUA LITRO', 'PAN', 'MARISCADA 2 PAX', 'PULPO A LA GALLEGA']; // Actualizado con los nuevos artículos
                const missingItems = expectedItems.filter(item => !contenidoPaso2.includes(item));
                if (missingItems.length > 0) {
                    console.error(`P2 CHECK FAIL: Faltan los siguientes artículos del ticket original: ${missingItems.join(', ')}`);
                }
                return missingItems.length === 0;
            }
        });

        await check(bodyPaso2, {
            'P2: totales correctos restaurante': () => { // Check síncrono
                // TODO: Actualizar estos totales con los valores correctos del ticket actual
                // const expectedTotals = ['SUBTOTAL_CORRECTO', 'IMPUESTOS_CORRECTOS', 'TOTAL_CORRECTO']; 
                const expectedTotals = ['2.50', '1.80', '22.00']; // Usando precios unitarios como placeholder, SE NECESITA ACTUALIZAR
                const missingTotals = expectedTotals.filter(item => !contenidoPaso2.includes(item));
                if (missingTotals.length > 0) {
                    console.error(`P2 CHECK FAIL: Faltan los siguientes totales del ticket original: ${missingTotals.join(', ')}`);
                }
                return missingTotals.length === 0;
            }
        });
        console.log('Verificaciones del Paso 2 completadas.');
        // --- FIN DE VERIFICACIONES DEL PASO 2 ---

        // console.log('Paso 2: Revisión de artículos completada.'); // Este log ya no es tan necesario aquí
        sleep(2); // Mantener la pausa si es útil para la visualización

        // --- PASO 2 a PASO 3: Hacer clic en "Continuar a asignación" ---
        console.log('Intentando hacer clic en "Continuar a asignación"...');
        const continuarBtnText = 'Continuar a asignación'; // Texto exacto del botón
        let continuarBtnHandle = null;
        const allButtonsPaso2 = await page.$$('button');
        for (const btnHandle of allButtonsPaso2) {
            const text = await btnHandle.textContent();
            if (text && text.trim() === continuarBtnText) {
                continuarBtnHandle = btnHandle;
                break;
            }
        }

        if (!continuarBtnHandle) {
            console.error(`CRITICAL: No se encontró el botón "${continuarBtnText}".`);
            await page.screenshot({ path: 'debug_no_continuar_btn.png' });
            throw new Error(`No se encontró el botón "${continuarBtnText}"`);
        }

        try {
            await continuarBtnHandle.click({ force: true, timeout: 10000 });
            console.log(`Botón "${continuarBtnText}" clicado exitosamente (con force=true).`);
        } catch (clickError) {
            console.error(`ERROR CRÍTICO al hacer clic en "${continuarBtnText}": ${clickError.message}`);
            await page.screenshot({ path: 'debug_continuar_btn_clic_fallido.png' });
            throw clickError;
        }

        console.log('Esperando a que cargue el Paso 3: Asignar personas...');
        sleep(3); // Espera para la transición al siguiente paso

        // --- PASO 3: Añadir personas "Cristian" y "Cbarba" ---
        console.log('Paso 3: Añadiendo personas...');
        const personasParaAnadir = ["Cristian", "Cbarba"];
        const inputSelectorPersonas = 'input[placeholder="Nombre de la persona"]';

        for (const persona of personasParaAnadir) {
            console.log(`Intentando añadir a: ${persona}`);
            
            const inputNombre = await page.$(inputSelectorPersonas);
            if (!inputNombre) {
                const errorMsg = `CRITICAL: No se encontró el input para añadir personas con selector: ${inputSelectorPersonas}`;
                console.error(errorMsg);
                await page.screenshot({ path: `debug_no_input_personas_${persona}.png` });
                throw new Error(errorMsg);
            }
            // Limpiar el input antes de escribir, por si acaso
            await inputNombre.evaluate(input => input.value = ''); 
            await inputNombre.type(persona, { delay: 100 });
            console.log(`Nombre "${persona}" escrito en el input.`);
            sleep(0.5);

            // Localizar y hacer clic en el botón "Añadir" que está junto al input de nombre
            let btnAnadir = null;
            const allButtonsPaso3 = await page.$$('button');
            for (const btnHandle of allButtonsPaso3) {
                const text = await btnHandle.textContent();
                // Buscamos un botón que contenga exactamente el texto "Añadir" y esté visible.
                // Podríamos añadir comprobaciones de proximidad al input si fuera necesario.
                if (text && text.trim() === 'Añadir') {
                    if (await btnHandle.isVisible()) {
                        btnAnadir = btnHandle;
                        break;
                    }
                }
            }
            
            if (!btnAnadir) {
                const errorMsg = `CRITICAL: No se encontró el botón "Añadir" visible para ${persona}.`;
                console.error(errorMsg);
                await page.screenshot({ path: `debug_no_btn_anadir_${persona}.png` });
                throw new Error(errorMsg);
            }
            
            console.log('Botón "Añadir" encontrado, intentando clic...');
            await btnAnadir.click({ force: true, timeout: 5000 });
            console.log(`Botón "Añadir" clicado para ${persona}.`);
            // Esperar a que la UI se actualice y el nombre aparezca en la lista (o el input se limpie)
            // Una forma de esperar es que el input vuelva a estar vacío
            try {
                await page.waitForFunction((selector) => {
                    const inputElement = document.querySelector(selector);
                    return inputElement && inputElement.value === '';
                }, inputSelectorPersonas, { timeout: 5000 });
                console.log(`Input de personas vacío después de añadir a ${persona}. UI actualizada.`);
            } catch (e) {
                console.warn(`Advertencia: El input de personas no se vació después de añadir a ${persona} o no se pudo verificar.`);
                // Considerar tomar screenshot aquí si esto es un problema recurrente
                // await page.screenshot({ path: `debug_input_no_vacio_${persona}.png` });
                sleep(1); // Pausa alternativa si la espera de función falla
            }
        }

        console.log('Todas las personas especificadas han sido procesadas.');
        
        // --- PASO 3b: Asignar artículos a las personas ---
        console.log('Paso 3b: Asignando artículos...');

        const asignaciones = [
            { itemNombre: 'AGUA LITRO', personas: ['Cristian', 'Cbarba'] },
            { itemNombre: 'PAN', personas: ['Cbarba'] },
            { itemNombre: 'MARISCADA', personas: ['Cbarba'] },
            { itemNombre: 'PULPO A LA GALLEGA', personas: ['Cristian', 'Cbarba'] },
            { itemNombre: 'COQUINAS', personas: ['Cristian'] },
        ];

        // Primero, obtener todos los contenedores de items (Card)
        // Cada item está en un <Card> que contiene un <CardHeader> con un <CardTitle>
        // Las Card de los ítems están dentro de un div.space-y-4 y tienen clases .overflow-hidden.shadow-sm
        const todosItemCards = await page.$$('div.space-y-4 > div.overflow-hidden.shadow-sm'); 

        console.log(`Encontrados ${todosItemCards.length} cards de items potenciales.`);

        for (const asignacion of asignaciones) {
            console.log(`Asignando "${asignacion.itemNombre}" a ${asignacion.personas.join(', ')}`);
            let itemCardHandle = null;

            for (const card of todosItemCards) {
                // Dentro de la card, buscar el CardTitle por sus clases específicas
                const titleHandle = await card.$('.text-lg.font-semibold'); 
                if (titleHandle) {
                    const tituloTexto = await titleHandle.textContent();
                    const tituloNormalizado = tituloTexto ? tituloTexto.trim().toUpperCase() : '[TÍTULO NO ENCONTRADO O VACÍO]';
                    const buscandoNormalizado = asignacion.itemNombre.toUpperCase();
                    
                    console.log(`  - Card detectada. Título leído: "${tituloTexto}" (Normalizado: "${tituloNormalizado}"). Buscando: "${buscandoNormalizado}"`);

                    if (tituloNormalizado.includes(buscandoNormalizado)) {
                        itemCardHandle = card;
                        console.log(`    ✓ Card encontrada para "${asignacion.itemNombre}"`);
                        break;
                    }
                }
            }

            if (!itemCardHandle) {
                const errorMsg = `CRITICAL: No se encontró el card del artículo "${asignacion.itemNombre}".`;
                console.error(errorMsg);
                await page.screenshot({ path: `debug_no_item_card_${asignacion.itemNombre.replace(/\s+/g, '_')}.png` });
                throw new Error(errorMsg);
            }

            // Dentro del card del item, buscar las etiquetas de asignación para las personas especificadas
            const labelsEnItemCard = await itemCardHandle.$$('label');
            for (const personaNombre of asignacion.personas) {
                console.log(`Intentando asignar "${asignacion.itemNombre}" a "${personaNombre}"`);
                let labelPersonaHandle = null;
                for (const label of labelsEnItemCard) {
                    const spanHandle = await label.$('span'); // El nombre de la persona está en un span dentro del label
                    if (spanHandle) {
                        const spanTexto = await spanHandle.textContent();
                        if (spanTexto && spanTexto.trim() === personaNombre) {
                            labelPersonaHandle = label;
                            break;
                        }
                    }
                }

                if (!labelPersonaHandle) {
                    const errorMsg = `CRITICAL: No se encontró la etiqueta de asignación para "${personaNombre}" en el artículo "${asignacion.itemNombre}".`;
                    console.error(errorMsg);
                    // Log para depurar los spans encontrados dentro de las labels de esta card
                    console.log(`DEBUG: Spans encontrados en las labels de la card "${asignacion.itemNombre}":`);
                    for (const lbl of labelsEnItemCard) {
                        const spanH = await lbl.$('span');
                        if (spanH) {
                            const txt = await spanH.textContent();
                            console.log(`  - Label con span: "${txt ? txt.trim() : "[SPAN VACÍO O NO ENCONTRADO EN LABEL]"}"`);
                        } else {
                            console.log("  - Label sin span interno encontrado.");
                        }
                    }
                    await page.screenshot({ path: `debug_no_label_${personaNombre}_${asignacion.itemNombre.replace(/\s+/g, '_')}.png` });
                    throw new Error(errorMsg);
                }

                // Verificar si ya está seleccionado (si la label tiene la clase bg-primary/10)
                const labelClassName = await labelPersonaHandle.getAttribute('class');
                const yaSeleccionado = labelClassName && labelClassName.includes('bg-primary/10');

                if (!yaSeleccionado) {
                    console.log(`"${personaNombre}" no está seleccionado para "${asignacion.itemNombre}". Haciendo clic.`);
                    await labelPersonaHandle.click({ force: true, timeout: 3000 }); // Clic en la etiqueta
                    sleep(0.5); // Pequeña pausa para que la UI reaccione
                } else {
                    console.log(`"${personaNombre}" ya está seleccionado para "${asignacion.itemNombre}". No se hace clic.`);
                }
            }
        }

        console.log('Todas las asignaciones de artículos han sido procesadas.');
        sleep(1);

        // --- PASO 3c: Hacer clic en "Calcular división" ---
        console.log('Intentando hacer clic en "Calcular división"...');
        let btnCalcular = null;
        const allButtonsPaso3Final = await page.$$('button');
        for (const btnHandle of allButtonsPaso3Final) {
            const text = await btnHandle.textContent();
            if (text && text.includes('Calcular división')) {
                btnCalcular = btnHandle;
                break;
            }
        }

        if (!btnCalcular) {
            const errorMsg = 'CRITICAL: No se encontró el botón "Calcular división".';
            console.error(errorMsg);
            await page.screenshot({ path: 'debug_no_btn_calcular.png' });
            throw new Error(errorMsg);
        }

        await btnCalcular.click({ force: true, timeout: 10000 });
        console.log('Botón "Calcular división" clicado exitosamente.');
        
        console.log('Esperando 5 segundos para la carga de la página de Resultados (Paso 4)...');
        sleep(5); // Espera para la carga de resultados

        // --- VERIFICACIONES DEL PASO 4: RESULTADOS ---
        console.log('Realizando verificaciones del Paso 4: Resultados de la división...');
        const bodyPaso4 = await page.locator('body');
        const contenidoPaso4 = await bodyPaso4.textContent();

        await check(bodyPaso4, {
            'P4: Se muestra el título de Resultados': () => contenidoPaso4.includes('Resultados de la división'),
            'P4: Se muestra a Cristian en los resultados': () => contenidoPaso4.includes('Cristian'),
            'P4: Se muestra a Cbarba en los resultados': () => contenidoPaso4.includes('Cbarba'),
            // Podríamos añadir aquí verificaciones más específicas de los montos si los conocemos
            // Por ejemplo: 'P4: Cristian paga X.XX': () => contenidoPaso4.includes('Cristian') && contenidoPaso4.includes('X.XX'),
        });
        console.log('Verificaciones del Paso 4 completadas.');
        // --- FIN DE VERIFICACIONES DEL PASO 4 ---

        console.log("FIN DEL TEST E2E REALIZADO CON ÉXITO."); // Mensaje de éxito final

    } finally {
        await page.close();
    }
} 