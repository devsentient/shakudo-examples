'use client'
import type { FC } from 'react'
import React, { useCallback, useRef, useState } from 'react'
import copy from 'copy-to-clipboard'
import cn from 'classnames'
import PromptEditorHeightResizeWrap from './prompt-editor-height-resize-wrap'
import ToggleExpandBtn from './toggle-expand-btn'
import useToggleExpend from './use-toggle-expend'
import { Clipboard, ClipboardCheck } from '@/app/components/base/icons/line/files'

type Props = {
  className?: string
  title: JSX.Element | string
  headerRight?: JSX.Element
  children: JSX.Element
  minHeight?: number
  value: string
  isFocus: boolean
}

const Base: FC<Props> = ({
  className,
  title,
  headerRight,
  children,
  minHeight = 120,
  value,
  isFocus,
}) => {
  const ref = useRef<HTMLDivElement>(null)
  const {
    wrapClassName,
    isExpand,
    setIsExpand,
    editorExpandHeight,
  } = useToggleExpend({ ref, hasFooter: false })

  const editorContentMinHeight = minHeight - 28
  const [editorContentHeight, setEditorContentHeight] = useState(editorContentMinHeight)

  const [isCopied, setIsCopied] = React.useState(false)
  const handleCopy = useCallback(() => {
    copy(value)
    setIsCopied(true)
  }, [value])

  return (
    <div className={cn(wrapClassName)}>
      <div ref={ref} className={cn(className, isExpand && 'h-full', 'rounded-lg border', isFocus ? 'bg-white border-gray-200' : 'bg-gray-100 border-gray-100 overflow-hidden')}>
        <div className='flex justify-between items-center h-7 pt-1 pl-3 pr-2'>
          <div className='text-xs font-semibold text-gray-700'>{title}</div>
          <div className='flex items-center'>
            {headerRight}
            {!isCopied
              ? (
                <Clipboard className='mx-1 w-3.5 h-3.5 text-gray-500 cursor-pointer' onClick={handleCopy} />
              )
              : (
                <ClipboardCheck className='mx-1 w-3.5 h-3.5 text-gray-500' />
              )
            }
            <div className='ml-1'>
              <ToggleExpandBtn isExpand={isExpand} onExpandChange={setIsExpand} />
            </div>
          </div>
        </div>
        <PromptEditorHeightResizeWrap
          height={isExpand ? editorExpandHeight : editorContentHeight}
          minHeight={editorContentMinHeight}
          onHeightChange={setEditorContentHeight}
          hideResize={isExpand}
        >
          <div className='h-full pb-2'>
            {children}
          </div>
        </PromptEditorHeightResizeWrap>
      </div>
    </div>
  )
}
export default React.memo(Base)
