---
title: '{{ replace .File.ContentBaseName "-" " " | title }}'
issue: {{ int (strings.TrimLeft "0" .File.ContentBaseName | default "0") }}
date: '{{ .Date }}'
draft: true
description: ""
external_url: ""
---
