import { electronAPI } from '@electron-toolkit/preload'
import { contextBridge } from 'electron'

contextBridge.exposeInMainWorld('electron', electronAPI)
