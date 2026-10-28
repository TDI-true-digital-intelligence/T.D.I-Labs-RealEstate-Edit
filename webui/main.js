// RealEstate Edit — native app shell
// Cloned from the PROVEN Echo webui recipe (Sep–Oct 2026): minimal Electron
// window with its own identity loading the RealEstate Edit app at :8189.

const { app, BrowserWindow, shell } = require('electron')
const path = require('path')

// EPIPE guard — logging must never be fatal.
process.stdout && process.stdout.on && process.stdout.on('error', (e) => { if (e.code === 'EPIPE') {} })
process.stderr && process.stderr.on && process.stderr.on('error', (e) => { if (e.code === 'EPIPE') {} })
process.on('uncaughtException', (e) => {
  if (e && e.code === 'EPIPE') return
  console.error('[realestate-uncaught]', e)
})

const APP_URL = process.env.REALESTATE_URL || 'http://127.0.0.1:8189/'
const ICON = path.join(__dirname, 'icon.png')

app.disableHardwareAcceleration()
app.setName('RealEstate Edit')
if (process.platform === 'linux') {
  app.commandLine.appendSwitch('class', 'realestate-edit')
  app.commandLine.appendSwitch('name', 'RealEstate Edit')
  process.env.ELECTRON_OZONE_PLATFORM_HINT = 'x11'
}

const gotLock = app.requestSingleInstanceLock()
if (!gotLock) app.quit()

function createWindow() {
  const win = new BrowserWindow({
    width: 1280, height: 860, minWidth: 900, minHeight: 600,
    title: 'RealEstate Edit',
    icon: ICON,
    backgroundColor: '#0a0e1a',
    autoHideMenuBar: true,
    show: true,
    webPreferences: { contextIsolation: true, nodeIntegration: false },
  })
  win.show(); win.focus()
  win.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith('http://127.0.0.1:8189')) return { action: 'allow' }
    shell.openExternal(url); return { action: 'deny' }
  })

  let healAttempts = 0
  const heal = (why) => {
    healAttempts++
    const delay = Math.min(2000 * Math.pow(2, healAttempts - 1), 8000)
    console.log(`[realestate-heal] ${why} (attempt ${healAttempts}, reload in ${delay}ms)`)
    setTimeout(() => { try { win.webContents.reload() } catch (e) {} }, delay)
  }
  win.webContents.on('render-process-gone', (_e, d) => heal(`gone: ${d.reason}`))
  win.webContents.on('unresponsive', () => heal('unresponsive'))
  win.webContents.on('did-fail-load', (_e, code, desc, url, isMain) => {
    if (isMain && code !== -3) heal(`did-fail-load ${code} ${desc}`)
  })
  win.loadURL(APP_URL)
}

app.whenReady().then(() => {
  createWindow()
  app.on('second-instance', () => {
    const all = BrowserWindow.getAllWindows()
    if (all.length) { if (all[0].isMinimized()) all[0].restore(); all[0].focus() }
  })
  app.on('activate', () => { if (BrowserWindow.getAllWindows().length === 0) createWindow() })
})
app.on('window-all-closed', () => app.quit())
