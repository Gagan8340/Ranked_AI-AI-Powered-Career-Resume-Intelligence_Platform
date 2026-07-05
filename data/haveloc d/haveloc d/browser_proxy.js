// Copyright 2021 The Chromium Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.
import{PageCallbackRouter,PageHandler}from"./color_change_listener.mojom-webui.js";let instance=null;export class BrowserProxy{callbackRouter;constructor(){this.callbackRouter=new PageCallbackRouter;const pageHandlerRemote=PageHandler.getRemote();pageHandlerRemote.setPage(this.callbackRouter.$.bindNewPipeAndPassRemote())}static getInstance(){return instance||(instance=new BrowserProxy)}static setInstance(newInstance){instance=newInstance}}