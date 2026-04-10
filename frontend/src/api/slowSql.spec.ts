import { beforeEach, describe, expect, it, vi } from 'vitest'

const { elMessageErrorMock, elMessageSuccessMock } = vi.hoisted(() => ({
  elMessageErrorMock: vi.fn(),
  elMessageSuccessMock: vi.fn()
}))

vi.mock('element-plus', () => ({
  ElMessage: {
    error: elMessageErrorMock,
    success: elMessageSuccessMock
  }
}))

import { downloadSlowSQL } from './slowSql'

describe('slowSql api download', () => {
  beforeEach(() => {
    vi.clearAllMocks()

    vi.spyOn(console, 'error').mockImplementation(() => undefined)
    vi.spyOn(window, 'open').mockImplementation(() => null)
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => undefined)

    if (!('createObjectURL' in URL)) {
      Object.defineProperty(URL, 'createObjectURL', {
        writable: true,
        value: vi.fn()
      })
    }
    if (!('revokeObjectURL' in URL)) {
      Object.defineProperty(URL, 'revokeObjectURL', {
        writable: true,
        value: vi.fn()
      })
    }

    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        blob: () => Promise.resolve(new Blob(['markdown'])),
        headers: new Headers({
          'Content-Disposition': 'attachment; filename="slow_sql_abc123_optimization.md"'
        })
      })
    )

    vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:mock-url')
    vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => undefined)
  })

  it('downloads via fetch instead of opening a blank page', async () => {
    await downloadSlowSQL('abc123')

    expect(fetch).toHaveBeenCalledWith('/api/slow-sqls/abc123/download', {
      method: 'GET'
    })
    expect(window.open).not.toHaveBeenCalled()
    expect(elMessageSuccessMock).toHaveBeenCalledWith('下载成功')
  })

  it('shows error message when download request fails', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        json: () => Promise.resolve({ error: '下载失败' })
      })
    )

    await downloadSlowSQL('abc123')

    expect(elMessageErrorMock).toHaveBeenCalledWith('下载失败')
  })
})
