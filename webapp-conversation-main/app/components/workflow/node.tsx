'use client'
import type { FC } from 'react'
import { useEffect, useState } from 'react'
import cn from 'classnames'
import BlockIcon from './block-icon'
import CodeEditor from './code-editor'
import { CodeLanguage } from '@/types/app'
import AlertCircle from '@/app/components/base/icons/line/alert-circle'
import AlertTriangle from '@/app/components/base/icons/line/alert-triangle'
import Loading02 from '@/app/components/base/icons/line/loading-02'
import CheckCircle from '@/app/components/base/icons/line/check-circle'
import ChevronRight from '@/app/components/base/icons/line/chevron-right'
import type { NodeTracing } from '@/types/app'

type Props = {
  nodeInfo: NodeTracing
  hideInfo?: boolean
}

const NodePanel: FC<Props> = ({ nodeInfo, hideInfo = false }) => {
  const [collapseState, setCollapseState] = useState<boolean>(true)

  const getTime = (time: number) => {
    if (time < 1)
      return `${(time * 1000).toFixed(3)} ms`
    if (time > 60)
      return `${parseInt(Math.round(time / 60).toString())} m ${(time % 60).toFixed(3)} s`
    return `${time.toFixed(3)} s`
  }

  const getTokenCount = (tokens: number) => {
    if (tokens < 1000)
      return tokens
    if (tokens >= 1000 && tokens < 1000000)
      return `${parseFloat((tokens / 1000).toFixed(3))}K`
    if (tokens >= 1000000)
      return `${parseFloat((tokens / 1000000).toFixed(3))}M`
  }

  useEffect(() => {
    setCollapseState(!nodeInfo.expand)
  }, [nodeInfo.expand])

  return (
    <div className={cn('px-4 py-1', hideInfo && '!p-0')}>
      <div className={cn('group transition-all bg-white border border-gray-100 rounded-2xl shadow-xs hover:shadow-md', hideInfo && '!rounded-lg')}>
        <div
          className={cn(
            'flex items-center pl-[6px] pr-3 cursor-pointer',
            hideInfo ? 'py-2' : 'py-3',
            !collapseState && (hideInfo ? '!pb-1' : '!pb-2'),
          )}
          onClick={() => setCollapseState(!collapseState)}
        >
          <ChevronRight
            className={cn(
              'shrink-0 w-3 h-3 mr-1 text-gray-400 transition-all group-hover:text-gray-500',
              !collapseState && 'rotate-90',
            )}
          />
          <BlockIcon size={hideInfo ? 'xs' : 'sm'} className={cn('shrink-0 mr-2', hideInfo && '!mr-1')} type={nodeInfo.node_type} toolIcon={nodeInfo.extras?.icon || nodeInfo.extras} />
          <div className={cn(
            'grow text-gray-700 text-[13px] leading-[16px] font-semibold truncate',
            hideInfo && '!text-xs',
          )} title={nodeInfo.title}>{nodeInfo.title}</div>
          {nodeInfo.status !== 'running' && !hideInfo && (
            <div className='shrink-0 text-gray-500 text-xs leading-[18px]'>{`${getTime(nodeInfo.elapsed_time || 0)} · ${getTokenCount(nodeInfo.execution_metadata?.total_tokens || 0)} tokens`}</div>
          )}
          {nodeInfo.status === 'succeeded' && (
            <CheckCircle className='shrink-0 ml-2 w-3.5 h-3.5 text-[#12B76A]' />
          )}
          {nodeInfo.status === 'failed' && (
            <AlertCircle className='shrink-0 ml-2 w-3.5 h-3.5 text-[#F04438]' />
          )}
          {nodeInfo.status === 'stopped' && (
            <AlertTriangle className='shrink-0 ml-2 w-3.5 h-3.5 text-[#F79009]' />
          )}
          {nodeInfo.status === 'running' && (
            <div className='shrink-0 flex items-center text-primary-600 text-[13px] leading-[16px] font-medium'>
              <Loading02 className='mr-1 w-3.5 h-3.5 animate-spin' />
              <span>Running</span>
            </div>
          )}
        </div>
        {!collapseState && (
          <div className='pb-2'>
            <div className={cn('px-[10px] py-1', hideInfo && '!px-2 !py-0.5')}>
              {nodeInfo.status === 'failed' && (
                <div className='px-3 py-[10px] bg-[#fef3f2] rounded-lg border-[0.5px] border-[rbga(0,0,0,0.05)] text-xs leading-[18px] text-[#d92d20] shadow-xs'>{nodeInfo.error}</div>
              )}
            </div>
            {nodeInfo.inputs && (
              <div className={cn('px-[10px] py-1', hideInfo && '!px-2 !py-0.5')}>
                <CodeEditor
                  readOnly
                  title={<div>INPUT</div>}
                  language={CodeLanguage.json}
                  value={nodeInfo.inputs}
                  isJSONStringifyBeauty
                />
              </div>
            )}
            {nodeInfo.process_data && (
              <div className={cn('px-[10px] py-1', hideInfo && '!px-2 !py-0.5')}>
                <CodeEditor
                  readOnly
                  title={<div>PROCESS DATA</div>}
                  language={CodeLanguage.json}
                  value={nodeInfo.process_data}
                  isJSONStringifyBeauty
                />
              </div>
            )}
            {nodeInfo.outputs && (
              <div className={cn('px-[10px] py-1', hideInfo && '!px-2 !py-0.5')}>
                <CodeEditor
                  readOnly
                  title={<div>OUTPUT</div>}
                  language={CodeLanguage.json}
                  value={nodeInfo.outputs}
                  isJSONStringifyBeauty
                />
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

export default NodePanel
