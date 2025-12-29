import { useForm } from 'react-hook-form'
import React, { Fragment, useCallback, useState } from 'react'

import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { TranslationTool } from '@/models/enums/TranslationTool'
import { TranslationSettingsFormType } from '@/models/TranslationSettingsFormType'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form'
import { useAppContext } from '@/context/AppContext'

const Settings = () => {
  const [editMode, setEditMode] = useState(false)
  const { setAPIKey, setTranslationTool } = useAppContext()

  const form = useForm<TranslationSettingsFormType>({
    defaultValues: {
      APIKey: '',
      translationTool: TranslationTool.GOOGLE,
    },
  })
  const {
    handleSubmit,
    formState: { errors },
    watch,
    reset,
  } = form

  const onSubmit = useCallback((data: TranslationSettingsFormType) => {
    setAPIKey(data.APIKey)
    setTranslationTool(data.translationTool)
    setEditMode(false)
  }, [setTranslationTool, setAPIKey])

  const onCancel = useCallback(() => {
    reset()
    setEditMode(false)
  }, [reset])

  const onEditMode = useCallback(() => {
    setEditMode(true)
  }, [])

  return (
    <Form {...form}>
      <section className="bg-white mt-6 rounded-xl shadow-md p-3">
        <form id="settings" onSubmit={handleSubmit(onSubmit)}>
          <div className="flex items-center justify-between">
            <div>
              <h2 className="font-semibold text-base">Translation</h2>
              <p className="text-sm">Settings for translation</p>
            </div>
            <div className="gap-x-4 flex">
              {
                editMode ?
                  (
                    <Fragment>
                      <Button type="button" onClick={handleSubmit(onSubmit)}>Save</Button>
                      <Button variant="outline" onClick={onCancel}>Cancel</Button>
                    </Fragment>
                  ) : (
                    <Button onClick={onEditMode} type="button">Edit</Button>
                  )
              }
            </div>
          </div>
          <div className="flex justify-between mt-5">
            <FormField
              disabled={!editMode}
              control={form.control}
              name="translationTool"
              render={({ field }) => (
                <FormItem className="w-2/5 flex items-center gap-x-4">
                  <FormLabel className="shrink-0">Translation Tool</FormLabel>
                  <FormControl>
                    <Select onValueChange={field.onChange} defaultValue={field.value} disabled={!editMode}>
                      <SelectTrigger className="!mt-0">
                        <SelectValue placeholder="Language" />
                      </SelectTrigger>
                      <SelectContent>
                        {
                          Object.values(TranslationTool).map(tool => (
                            <SelectItem value={tool} key={tool}>
                              {tool}
                            </SelectItem>
                          ))
                        }
                      </SelectContent>
                    </Select>
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            {watch('translationTool') === TranslationTool.DEEPL && (
              <FormField
                disabled={!editMode}
                control={form.control}
                name="APIKey"
                render={({ field }) => (
                  <FormItem className="w-2/5 flex items-center gap-x-4">
                    <FormLabel className="shrink-0">API Key</FormLabel>
                    <FormControl>
                      <Input placeholder="API Key" className="!mt-0" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            )}
          </div>
        </form>
      </section>
    </Form>
  )
}

export default Settings
