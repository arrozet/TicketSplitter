import { browser } from 'k6/browser';
import { check } from 'https://jslib.k6.io/k6-utils/1.5.0/index.js';
import { sleep } from 'k6';

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

        // Hacer el input visible y establecer su valor
        console.log('Haciendo el input visible...');
        await fileInput.evaluate(input => {
            input.style.display = 'block';
            input.style.visibility = 'visible';
            input.style.opacity = '1';
            input.style.position = 'static';
        });
        sleep(1);

        // Establecer el valor del input directamente
        console.log('Estableciendo el valor del input...');
        await fileInput.evaluate((input, path) => {
            input.value = path;
        }, 'tests/images/restaurante.jpg');
        sleep(1);

        // Disparar el evento change para que el frontend detecte el cambio
        console.log('Disparando evento change...');
        await fileInput.evaluate(input => {
            const event = new Event('change', { bubbles: true });
            input.dispatchEvent(event);
        });
        console.log('Archivo seleccionado. Esperando 2 segundos...');
        sleep(2);

        // Buscar y comprobar el botón "Subir y procesar"
        const procesarBtns = await page.$$('button');
        let subirBtn = null;
        for (const btn of procesarBtns) {
            const text = await btn.textContent();
            if (text && text.includes('Subir y procesar')) {
                subirBtn = btn;
                break;
            }
        }
        if (!subirBtn) {
            console.log('No se encontró el botón Subir y procesar');
            throw new Error('No se encontró el botón Subir y procesar');
        }
        const btnDisabled = await subirBtn.evaluate(btn => btn.disabled);
        console.log('Botón Subir y procesar encontrado. ¿Está deshabilitado?:', btnDisabled);
        sleep(2);

        // Hacer clic en el botón si está habilitado
        if (!btnDisabled) {
            await subirBtn.click();
            console.log('Botón Subir y procesar clicado.');
        } else {
            console.log('El botón Subir y procesar está deshabilitado. No se puede clicar.');
        }
        sleep(3);

        // Verificar que el ticket se procesó correctamente
        await check(page.locator('body'), {
            'ticket restaurante procesado': async (lo) => {
                const content = await lo.textContent();
                return content.includes('Café con leche') && 
                       content.includes('Tostada integral') &&
                       content.includes('Zumo naranja natural') &&
                       content.includes('Croissant mantequilla');
            }
        });

        // Verificar los totales
        await check(page.locator('body'), {
            'totales correctos restaurante': async (lo) => {
                const content = await lo.textContent();
                return content.includes('12.40') && // subtotal
                       content.includes('1.24') &&  // tax
                       content.includes('13.64');   // total
            }
        });

        sleep(2);

        // Subir el ticket de supermercado
        console.log('Subiendo ticket de supermercado...');
        await fileInput.setInputFiles('tests/images/supermercado.jpg');
        sleep(2);

        // Verificar que el ticket se procesó correctamente
        await check(page.locator('body'), {
            'ticket supermercado procesado': async (lo) => {
                const content = await lo.textContent();
                return content.includes('Leche desnatada') && 
                       content.includes('Pan integral') &&
                       content.includes('Manzanas Royal Gala') &&
                       content.includes('Descuento socio');
            }
        });

        sleep(2);

        // Subir el ticket de farmacia
        console.log('Subiendo ticket de farmacia...');
        await fileInput.setInputFiles('tests/images/farmacia.jpg');
        sleep(2);

        // Verificar que el ticket se procesó correctamente
        await check(page.locator('body'), {
            'ticket farmacia procesado': async (lo) => {
                const content = await lo.textContent();
                return content.includes('Paracetamol') && 
                       content.includes('Ibuprofeno') &&
                       content.includes('Vendas elásticas') &&
                       content.includes('Crema hidratante');
            }
        });

        // Verificar los totales de farmacia
        await check(page.locator('body'), {
            'totales correctos farmacia': async (lo) => {
                const content = await lo.textContent();
                return content.includes('14.20') && // subtotal
                       content.includes('0.00') &&  // tax
                       content.includes('14.20');   // total
            }
        });

    } finally {
        await page.close();
    }
} 