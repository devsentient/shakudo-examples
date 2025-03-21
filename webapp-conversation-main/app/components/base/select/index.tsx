'use client'
import type { FC } from 'react'
import React, { Fragment, useEffect, useState } from 'react'
import { Combobox, Listbox, Transition } from '@headlessui/react'
import classNames from 'classnames'
import { CheckIcon, ChevronDownIcon, ChevronUpIcon } from '@heroicons/react/20/solid'

const defaultItems = [
  { value: 1, name: 'option1' },
  { value: 2, name: 'option2' },
  { value: 3, name: 'option3' },
  { value: 4, name: 'option4' },
  { value: 5, name: 'option5' },
  { value: 6, name: 'option6' },
  { value: 7, name: 'option7' },
]

export type Item = {
  value: number | string
  name: string
}

export type ISelectProps = {
  className?: string
  items?: Item[]
  defaultValue?: number | string
  disabled?: boolean
  onSelect: (value: Item) => void
  allowSearch?: boolean
  bgClassName?: string
}
const Select: FC<ISelectProps> = ({
  className,
  items = defaultItems,
  defaultValue = 1,
  disabled = false,
  onSelect,
  allowSearch = true,
  bgClassName = 'bg-gray-100',
}) => {
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)

  const [selectedItem, setSelectedItem] = useState<Item | null>(null)
  useEffect(() => {
    let defaultSelect = null
    const existed = items.find((item: Item) => item.value === defaultValue)
    if (existed)
      defaultSelect = existed

    setSelectedItem(defaultSelect)
  }, [defaultValue])

  const filteredItems: Item[]
    = query === ''
      ? items
      : items.filter((item) => {
        return item.name.toLowerCase().includes(query.toLowerCase())
      })

  return (
    <Combobox
      as="div"
      disabled={disabled}
      value={selectedItem}
      className={className}
      onChange={(value: Item) => {
        if (!disabled) {
          setSelectedItem(value)
          setOpen(false)
          onSelect(value)
        }
      }}>
      <div className={classNames('relative')}>
        <div className='group text-gray-800'>
          {allowSearch
            ? <Combobox.Input
              className={`w-full rounded-lg border-0 ${bgClassName} py-1.5 pl-3 pr-10 shadow-sm sm:text-sm sm:leading-6 focus-visible:outline-none focus-visible:bg-gray-200 group-hover:bg-gray-200 cursor-not-allowed`}
              onChange={(event) => {
                if (!disabled)
                  setQuery(event.target.value)
              }}
              displayValue={(item: Item) => item?.name}
            />
            : <Combobox.Button onClick={
              () => {
                if (!disabled)
                  setOpen(!open)
              }
            } className={`flex items-center h-9 w-full rounded-lg border-0 ${bgClassName} py-1.5 pl-3 pr-10 shadow-sm sm:text-sm sm:leading-6 focus-visible:outline-none focus-visible:bg-gray-200 group-hover:bg-gray-200`}>
              {selectedItem?.name}
            </Combobox.Button>}
          <Combobox.Button className="absolute inset-y-0 right-0 flex items-center rounded-r-md px-2 focus:outline-none group-hover:bg-gray-200" onClick={
            () => {
              if (!disabled)
                setOpen(!open)
            }
          }>
            {open ? <ChevronUpIcon className="h-5 w-5" /> : <ChevronDownIcon className="h-5 w-5" />}
          </Combobox.Button>
        </div>

        {filteredItems.length > 0 && (
          <Combobox.Options className="absolute z-10 mt-1 px-1 max-h-60 w-full overflow-auto rounded-md bg-white py-1 text-base shadow-lg border-gray-200 border-[0.5px] focus:outline-none sm:text-sm">
            {filteredItems.map((item: Item) => (
              <Combobox.Option
                key={item.value}
                value={item}
                className={({ active }: { active: boolean }) =>
                  classNames(
                    'relative cursor-default select-none py-2 pl-3 pr-9 rounded-lg hover:bg-gray-100 text-gray-700',
                    active ? 'bg-gray-100' : '',
                  )
                }
              >
                {({ /* active, */ selected }) => (
                  <>
                    <span className={classNames('block truncate', selected && 'font-normal')}>{item.name}</span>
                    {selected && (
                      <span
                        className={classNames(
                          'absolute inset-y-0 right-0 flex items-center pr-4 text-gray-700',
                        )}
                      >
                        <CheckIcon className="h-5 w-5" aria-hidden="true" />
                      </span>
                    )}
                  </>
                )}
              </Combobox.Option>
            ))}
          </Combobox.Options>
        )}
      </div>
    </Combobox >
  )
}

const SimpleSelect: FC<ISelectProps> = ({
  className,
  items = defaultItems,
  defaultValue = 1,
  disabled = false,
  onSelect,
}) => {
  const [selectedItem, setSelectedItem] = useState<Item | null>(null)
  useEffect(() => {
    let defaultSelect = null
    const existed = items.find((item: Item) => item.value === defaultValue)
    if (existed)
      defaultSelect = existed

    setSelectedItem(defaultSelect)
  }, [defaultValue])

  return (
    <Listbox
      value={selectedItem}
      onChange={(value: Item) => {
        if (!disabled) {
          setSelectedItem(value)
          onSelect(value)
        }
      }}
    >
      <div className="relative h-9">
        <Listbox.Button className={`w-full h-full rounded-lg border-0 bg-gray-100 py-1.5 pl-3 pr-10 shadow-sm sm:text-sm sm:leading-6 focus-visible:outline-none focus-visible:bg-gray-200 group-hover:bg-gray-200 cursor-pointer ${className}`}>
          <span className="block truncate text-left">{selectedItem?.name}</span>
          <span className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-2">
            <ChevronDownIcon
              className="h-5 w-5 text-gray-400"
              aria-hidden="true"
            />
          </span>
        </Listbox.Button>
        <Transition
          as={Fragment}
          leave="transition ease-in duration-100"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <Listbox.Options className="absolute z-10 mt-1 px-1 max-h-60 w-full overflow-auto rounded-md bg-white py-1 text-base shadow-lg border-gray-200 border-[0.5px] focus:outline-none sm:text-sm">
            {items.map((item: Item) => (
              <Listbox.Option
                key={item.value}
                className={({ active }) =>
                  `relative cursor-pointer select-none py-2 pl-3 pr-9 rounded-lg hover:bg-gray-100 text-gray-700 ${active ? 'bg-gray-100' : ''
                  }`
                }
                value={item}
                disabled={disabled}
              >
                {({ /* active, */ selected }) => (
                  <>
                    <span className={classNames('block truncate', selected && 'font-normal')}>{item.name}</span>
                    {selected && (
                      <span
                        className={classNames(
                          'absolute inset-y-0 right-0 flex items-center pr-4 text-gray-700',
                        )}
                      >
                        <CheckIcon className="h-5 w-5" aria-hidden="true" />
                      </span>
                    )}
                  </>
                )}
              </Listbox.Option>
            ))}
          </Listbox.Options>
        </Transition>
      </div>
    </Listbox>
  )
}
export { SimpleSelect }
export default React.memo(Select)
