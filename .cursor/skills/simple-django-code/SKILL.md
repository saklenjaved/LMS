---
name: simple-django-code
description: Writes intern-level Django for this LMS — short functions, basic ModelForm, admin.site.register. Use when adding or editing Python in this project, or when the user asks for simple code.
---

# Simple Django code

Write code a student can type by hand.

## Do

- Short function views for new pages
- `ModelForm` with `Meta.fields` only
- `admin.site.register(Model)`
- Models = fields + `__str__`
- One `if` for role or status

## Do not

- New mixin / CBV stacks
- Custom `ModelAdmin` classes, inlines, fieldsets
- Form `__init__` or form helper classes
- Services, managers, serializers, REST

## Quiz score (keep in the view)

```python
passed = True
for q in questions:
    if request.POST.get("q_%s" % q.pk) != q.correct_option:
        passed = False
```
