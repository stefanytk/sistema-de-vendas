#Importando as bibliotecas
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import pandas as pd
import os
from tkcalendar import DateEntry
import unicodedata
from datetime import datetime, timedelta

#Pegando os .csv
ARQUIVO_ESTOQUE = 'estoque.csv'
ARQUIVO_VENDAS = 'historico_vendas.csv'

#Criando a classe produto
class Produto:
    def __init__(self, sku, nome, categoria, quantidade, unidade, preco, valor_compra, fornecedor,
                 data_entrada, validade, observacoes):
        self.sku = sku
        self.nome = nome
        self.categoria = categoria
        self.quantidade = quantidade
        self.unidade = unidade
        self.preco = preco
        self.valor_compra = valor_compra
        self.fornecedor = fornecedor
        self.data_entrada = data_entrada
        self.validade = validade
        self.observacoes = observacoes

#Acessando e alterando os dados do arquivo de estoque
class EstoqueCSV:
    def __init__(self, arquivo=ARQUIVO_ESTOQUE):
        self.arquivo = arquivo
        if not os.path.exists(self.arquivo):
            colunas = ["sku", "nome", "categoria", "quantidade", "unidade", "preco", "valor_compra",
                       "fornecedor", "data_entrada", "validade", "observacoes"]
            pd.DataFrame(columns=colunas).to_csv(self.arquivo, index=False)

    def listar_produtos(self):
        return pd.read_csv(self.arquivo)

    def salvar_produtos(self, df):
        df.to_csv(self.arquivo, index=False)

    def adicionar_produto(self, produto):
        df = self.listar_produtos()

        if produto.sku in df["sku"].astype(str).values:
            raise ValueError(f"O SKU '{produto.sku}' já existe no estoque!")

        novo = pd.DataFrame([vars(produto)])
        df = pd.concat([df, novo], ignore_index=True)
        self.salvar_produtos(df)

    def atualizar_produto(self, sku, coluna, novo_valor):
        df = self.listar_produtos()
        if coluna in df.columns:
            df.loc[df["sku"] == sku, coluna] = novo_valor
            self.salvar_produtos(df)

    def ajustar_quantidade(self, sku, delta):
        df = self.listar_produtos()
        idx = df.index[df["sku"] == sku]
        if not idx.empty:
            idx = idx[0]
            atual = df.at[idx, "quantidade"]
            novo = atual + delta
            if novo < 0:
                return False
            df.at[idx, "quantidade"] = novo
            self.salvar_produtos(df)
            return True
        return False
    
    def remover_produto(self, sku):
        df = self.listar_produtos()
        df = df[df["sku"] != sku] 
        self.salvar_produtos(df)
    
#Acessando e alterando os dados do arquivo de historico de vendas
class HistoricoVendas:
    def __init__(self, arquivo=ARQUIVO_VENDAS):
        self.arquivo = arquivo
        if not os.path.exists(self.arquivo):
            colunas = ["venda_id", "sku", "nome", "quantidade_vendida", "preco_unitario", "total", "data_venda"]
            pd.DataFrame(columns=colunas).to_csv(self.arquivo, index=False)

    def registrar_venda(self, vendas):
        df = pd.read_csv(self.arquivo)

        if not vendas:
            return

        data_venda = vendas[0]["data_venda"]  
        nova_id = 1

        if not df.empty and "data_venda" in df.columns and "venda_id" in df.columns:
            df_data = df[df["data_venda"] == data_venda]
            if not df_data.empty:
                nova_id = df_data["venda_id"].max() + 1

        for item in vendas:
            item["venda_id"] = nova_id

        nova_venda = pd.DataFrame(vendas)
        nova_venda = nova_venda.dropna(axis=1, how="all")

        df = pd.concat([df, nova_venda], ignore_index=True)
        df.to_csv(self.arquivo, index=False)

#Janela do controle de estoque
class AppEstoque:
    def __init__(self, root):
        self.db = EstoqueCSV()
        self.root = root
        self.root.title("estoque")
        self.root.configure(bg="#e0f0ff")

        try:
            self.root.state("zoomed")
        except tk.TclError:
            self.root.attributes("-fullscreen", True)
            def sair_fullscreen(event):
                self.root.attributes("-fullscreen", False)
            self.root.bind("<Escape>", sair_fullscreen)

        self.vars = {nome: tk.StringVar() for nome in ["sku", "nome", "categoria", "quantidade", "unidade", 
                    "preco", "valor_compra", "fornecedor", "data_entrada", "validade", "observacoes"]}

        form = tk.Frame(root, bg="#e0f0ff")
        form.pack(side="left", padx=20, pady=20, fill="y")

        for campo, label in self.vars.items():
            tk.Label(form, text=campo.capitalize(), bg="#e0f0ff", fg="#003366").pack(anchor="w")
            if "data" in campo or "validade" in campo:
                DateEntry(form, textvariable=label, date_pattern='yyyy-mm-dd').pack(fill="x")
            elif campo == "unidade":
                unidade_cb = ttk.Combobox(form, textvariable=label, values=["unidades", "kg", "litros", "cartelas", "pares", "conjuntos"], state="readonly")
                unidade_cb.pack(fill="x")
            else:
                tk.Entry(form, textvariable=label).pack(fill="x")

        tk.Button(form, text="Adicionar Produto", command=self.adicionarproduto,
                  bg="#007acc", fg="white").pack(pady=5)

        tk.Button(form, text="Voltar ao Menu", command=self.voltar_ao_menu,
                  bg="#cc3300", fg="white").pack(pady=15)

        tabela = tk.Frame(root, bg="#e0f0ff")
        tabela.pack(side="right", padx=20, pady=20, fill="both", expand=True)

        colunas = ["sku", "nome", "categoria", "quantidade", "unidade", "preco", "valor_compra",
                    "fornecedor", "data_entrada", "validade", "observacoes"]

        self.tree = ttk.Treeview(tabela, columns=colunas, show="headings")
        for col in colunas:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="center", width=100)
        self.tree.pack(fill="both", expand=True)

        self.tree.bind("<Double-1>", self.abrir_janela_produto)

        self.atualizar_lista()

#Botão para voltar ao menu
    def voltar_ao_menu(self):
        self.root.destroy()
        nova_root = tk.Tk()
        AppMenuInicial(nova_root)
        nova_root.mainloop()

#Botão para adicionar um produto
    def adicionarproduto(self):
        try:
            #Verificar se todos os campos estão preenchidos
            for nome, var in self.vars.items():
                if var.get().strip() == "":
                    raise ValueError(f"Por favor, preencha o campo '{nome}'.")

            #Validar SKU
            sku_str = self.vars["sku"].get()
            if not sku_str.isdigit() or int(sku_str) <= 0:
                raise ValueError("SKU deve ser um número inteiro positivo.")

            #Validar quantidade
            qtd_str = self.vars["quantidade"].get()
            if not qtd_str.isdigit() or int(qtd_str) <= 0:
                raise ValueError("Quantidade deve ser um número inteiro positivo.")

            #Validar preço
            preco_str = self.vars["preco"].get()
            try:
                preco = float(preco_str)
                if preco <= 0:
                    raise ValueError("Preço deve ser um número positivo.")
            except ValueError:
                raise ValueError("Preço deve ser um número válido (ex: 10.50).")

            #Validar valor de compra
            valor_compra_str = self.vars["valor_compra"].get()
            try:
                valor_compra = float(valor_compra_str)
                if valor_compra <= 0:
                    raise ValueError("Valor de compra deve ser um número positivo.")
            except ValueError:
                raise ValueError("Valor de compra deve ser um número válido (ex: 8.75).")
            
            #Normaliza a categoria (sem acento, primeira letra maiúscula)
            categoria = self.vars["categoria"].get()
            categoria = unicodedata.normalize("NFKD", categoria).encode("ASCII", "ignore").decode("utf-8")
            categoria = categoria.capitalize()  

            data_validade_str = self.vars["validade"].get()
            data_hoje = datetime.now().date()

            try:
                data_validade = datetime.strptime(data_validade_str, "%Y-%m-%d").date()
                if data_validade < data_hoje:
                    messagebox.showerror("Data Inválida", "Não é possível adicionar produtos com validade vencida.")
                    return
            except ValueError:
                messagebox.showerror("Erro de Formato", "A data de validade está em formato inválido.")
                return    

            # Criar produto 
            produto = Produto(
                sku=sku_str,
                nome=self.vars["nome"].get(),
                categoria=categoria,
                quantidade=int(qtd_str),
                unidade=self.vars["unidade"].get(),
                preco=preco,
                valor_compra=valor_compra,
                fornecedor=self.vars["fornecedor"].get(),
                data_entrada=self.vars["data_entrada"].get(),
                validade=self.vars["validade"].get(),
                observacoes=self.vars["observacoes"].get()
            )
            self.db.adicionar_produto(produto)
            self.atualizar_lista()
            for var in self.vars.values():
                var.set("")
        except ValueError as ve:
            messagebox.showerror("Erro de Validação", str(ve))
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao adicionar produto: {e}")


#Atualiza a tela quando alguma alteração for feita
    def atualizar_lista(self):
        for i in self.tree.get_children():
            self.tree.delete(i)

        df = self.db.listar_produtos().sort_values(by="sku")
        hoje = datetime.now().date()
        limite_validade = hoje + timedelta(days=7)

        for _, row in df.iterrows():
            data_validade_str = str(row["validade"])
            quantidade = int(row["quantidade"])

            validade_proxima = False
            estoque_baixo = quantidade <= 5

            #Verifica validade
            try:
                data_validade = datetime.strptime(data_validade_str, "%Y-%m-%d").date()
                validade_proxima = data_validade <= limite_validade
            except:
                validade_proxima = False 

            if validade_proxima and estoque_baixo:
                tag = "critico"
            elif validade_proxima:
                tag = "validade"
            elif estoque_baixo:
                tag = "estoque"
            else:
                tag = ""

            self.tree.insert("", tk.END, values=tuple(row), tags=(tag,))

        self.tree.tag_configure("validade", background="#f16e6e")   
        self.tree.tag_configure("estoque", background="#ee8c4a")    
        self.tree.tag_configure("critico", background="#c02626")    


#Janela com detalhes do pruduto
    def abrir_janela_produto(self, event):
        item_id = self.tree.focus()
        if not item_id:
            return
        dados = self.tree.item(item_id)["values"]
        if not dados:
            return

        colunas = ["sku", "nome", "categoria", "quantidade", "unidade", "preco", "valor_compra",
                   "fornecedor", "data_entrada", "validade", "observacoes"]
        produto_dict = dict(zip(colunas, dados))

        janela = tk.Toplevel(self.root)
        janela.title(f"Produto: {produto_dict['nome']} - Detalhes")
        janela.configure(bg="#e0f0ff")
        janela.geometry("400x420")

        for campo, valor in produto_dict.items():
            frame = tk.Frame(janela, bg="#e0f0ff")
            frame.pack(fill="x", padx=10, pady=3)
            tk.Label(frame, text=f"{campo}:", font=("Arial", 10, "bold"), bg="#e0f0ff").pack(side="left")
            tk.Label(frame, text=str(valor), bg="#e0f0ff").pack(side="left")

        def adicionar_quantidade():
            try:
                qtd_str = simpledialog.askstring("Adicionar Quantidade", "Digite a quantidade a adicionar:", parent=janela)
                if qtd_str is None:
                    return
                qtd = int(qtd_str)
                if qtd <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Valor Inválido", "Por favor, insira um número inteiro positivo.")
                return

            sucesso = self.db.ajustar_quantidade(produto_dict["sku"], qtd)
            if sucesso:
                messagebox.showinfo("Sucesso", f"{qtd} unidades adicionadas ao estoque.")
                self.atualizar_lista()
                janela.destroy()
            else:
                messagebox.showerror("Erro", "Houve um problema ao adicionar a quantidade.")

        def alterar_preco():
            try:
                novo_preco = simpledialog.askstring("Alterar Preço", "Digite o novo preço (ex: 19.99):", parent=janela)
                if novo_preco is None:
                    return
                novo_preco = float(novo_preco)
                if novo_preco < 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Preço Inválido", "Insira um valor numérico positivo, como 12.50.")
                return

            if novo_preco is None:
                return
            self.db.atualizar_produto(produto_dict["sku"], "preco", novo_preco)
            messagebox.showinfo("Sucesso", f"preco alterado para {novo_preco:.2f}.")
            self.atualizar_lista()
            janela.destroy()

        def remover_produto():
            confirmar = messagebox.askyesno("Confirmar Remoção", f"Deseja realmente remover o produto '{produto_dict['nome']}' do estoque?")
            if confirmar:
                self.db.remover_produto(produto_dict["sku"])
                messagebox.showinfo("Removido", f"Produto '{produto_dict['nome']}' removido com sucesso.")
                self.atualizar_lista()
                janela.destroy()

        botoes = tk.Frame(janela, bg="#e0f0ff")
        botoes.pack(pady=15)

        tk.Button(botoes, text="Adicionar Qtde", command=adicionar_quantidade, 
                  bg="#007acc", fg="white", width=12).pack(side="left", padx=5)
        tk.Button(botoes, text="Alterar preco", command=alterar_preco, 
                  bg="#007acc", fg="white", width=12).pack(side="left", padx=5)
        tk.Button(botoes, text="Remover Produto", command=remover_produto, 
                  bg="#cc0000", fg="white", width=14).pack(side="left", padx=5)
        tk.Button(janela, text="Fechar", command=janela.destroy, 
                  width=12).pack(pady=5)

#Janela de controle de vendas
class AppVendas:
    def __init__(self, root):
        self.root = root
        self.root.title("Vendas")
        self.db = EstoqueCSV()
        self.hist = HistoricoVendas()
        self.selecionados = {}

        try:
            self.root.state("zoomed")
        except tk.TclError:
            self.root.attributes("-fullscreen", True)
            def sair_fullscreen(event):
                self.root.attributes("-fullscreen", False)
            self.root.bind("<Escape>", sair_fullscreen)

        self.lista_produtos = self.db.listar_produtos()
        self.lista_produtos = self.lista_produtos.sort_values(by="sku")

        frame = tk.Frame(root)
        frame.pack(padx=10, pady=10, fill="both", expand=True)

        self.tree = ttk.Treeview(frame, columns=["sku", "nome", "estoque", "preco", "observacoes"], show="headings")
        for col in ["sku", "nome", "estoque", "preco", "observacoes"]:
            self.tree.heading(col, text=col.capitalize())
            self.tree.column(col, anchor="center", width=120)  

        self.tree.pack(fill="both", expand=True)

        for _, row in self.lista_produtos.iterrows():
            if int(row["quantidade"]) > 0:
                obs = row.get("observacoes", "") 
                self.tree.insert("", tk.END, values=(row["sku"], row["nome"], row["quantidade"], row["preco"], obs))


        tk.Button(root, text="Adicionar Produto", command=self.adicionar_produto, bg="#007acc", fg="white").pack(pady=5)
        tk.Button(root, text="Ver Carrinho", command=self.abrir_carrinho, bg="#ffaa00", fg="black").pack(pady=5)
        self.label_total = tk.Label(root, text="total: R$ 0.00", font=("Arial", 12, "bold"))
        self.label_total.pack(pady=5)
        tk.Button(root, text="Vender", command=self.realizar_venda, bg="#28a745", fg="white").pack(pady=5)
        tk.Button(root, text="Voltar ao Menu", command=self.voltar, bg="#cc3300", fg="white").pack(pady=5)

        self.data_venda = None
        popup = tk.Toplevel(self.root)
        popup.title("Selecionar Data da Venda")
        popup.geometry("300x150")
        popup.grab_set()
        popup.lift()
        popup.attributes("-topmost", True)
        popup.after(100, lambda: popup.attributes("-topmost", False))

        tk.Label(popup, text="Escolha a data da venda:", font=("Arial", 12)).pack(pady=10)
        calendario = DateEntry(popup, date_pattern='yyyy-mm-dd')
        calendario.pack(pady=5)

        def confirmar_data():
            self.data_venda = calendario.get()
            popup.destroy()
        tk.Button(popup, text="Confirmar", command=confirmar_data, bg="#007acc", fg="white").pack(pady=10)

        self.root.wait_window(popup)

        if not self.data_venda:
            messagebox.showwarning("Data inválida", "Você precisa informar uma data para continuar.")
            self.root.destroy()
            nova_root = tk.Tk()
            AppMenuInicial(nova_root)
            nova_root.mainloop()
            return

    def adicionar_produto(self):
        item = self.tree.focus()
        if not item:
            return
        valores = self.tree.item(item)["values"]
        sku, nome, estoque, preco, *resto = valores 
        estoque = int(estoque)
        preco = float(preco)

        qtd_str = simpledialog.askstring("Quantidade", f"Quantas unidades de '{nome}'?", parent=self.root)
        if qtd_str is None:
            return
        try:
            qtd = int(qtd_str)
            if qtd <= 0:
                raise ValueError
            qtd_existente = self.selecionados.get(sku, {}).get("quantidade_vendida", 0)
            if qtd + qtd_existente > estoque:
                messagebox.showerror("Estoque insuficiente", f"Disponível: {estoque - qtd_existente}")
                return
        except ValueError:
            messagebox.showerror("Valor Inválido", "Por favor, insira um número inteiro positivo.")
            return

        if sku in self.selecionados:
            self.selecionados[sku]["quantidade_vendida"] += qtd
            self.selecionados[sku]["total"] = self.selecionados[sku]["quantidade_vendida"] * preco
        else:
            self.selecionados[sku] = {
                "sku": sku,
                "nome": nome,
                "quantidade_vendida": qtd,
                "preco_unitario": preco,
                "total": qtd * preco,
                "data_venda": self.data_venda
            }
        self.atualizar_total()

    def abrir_carrinho(self):
        if not self.selecionados:
            messagebox.showinfo("Carrinho vazio", "Nenhum produto adicionado.")
            return

        janela = tk.Toplevel(self.root)
        janela.title("Carrinho de Compras")
        janela.geometry("600x400")

        colunas = ["sku", "nome", "quantidade", "preco_unitario", "total"]
        tree = ttk.Treeview(janela, columns=colunas, show="headings")
        for col in colunas:
            tree.heading(col, text=col.capitalize())
            tree.column(col, anchor="center")
        tree.pack(fill="both", expand=True, pady=10)

        for item in self.selecionados.values():
            tree.insert("", tk.END, values=(
                item["sku"],
                item["nome"],
                item["quantidade_vendida"],
                f"R$ {item['preco_unitario']:.2f}",
                f"R$ {item['total']:.2f}"
            ))

        def editar_quantidade():
            selected = tree.selection()
            if not selected:
                messagebox.showwarning("Seleção", "Selecione um produto para editar.")
                return
            iid = selected[0]
            valores = tree.item(iid)["values"]
            sku = valores[0]
            produto = self.selecionados[sku]

            qtd_str = simpledialog.askstring("Editar Quantidade",
                                             f"Quantidade atual de '{produto['nome']}' é {produto['quantidade_vendida']}. Novo valor:",
                                             parent=janela)
            if qtd_str is None:
                return
            try:
                nova_qtd = int(qtd_str)
                if nova_qtd <= 0:
                    raise ValueError
                estoque_total = next(row for row in self.lista_produtos.itertuples() if row.sku == sku).quantidade
                if nova_qtd > estoque_total:
                    messagebox.showerror("Estoque insuficiente", f"Disponível: {estoque_total}")
                    return
            except ValueError:
                messagebox.showerror("Valor Inválido", "Insira um número inteiro positivo.")
                return

            produto["quantidade_vendida"] = nova_qtd
            produto["total"] = nova_qtd * produto["preco_unitario"]

            tree.item(iid, values=(
                produto["sku"],
                produto["nome"],
                produto["quantidade_vendida"],
                f"R$ {produto['preco_unitario']:.2f}",
                f"R$ {produto['total']:.2f}"
            ))
            self.atualizar_total()

        def remover_produto():
            selected = tree.selection()
            if not selected:
                messagebox.showwarning("Seleção", "Selecione um produto para remover.")
                return
            iid = selected[0]
            valores = tree.item(iid)["values"]
            sku = valores[0]

            confirm = messagebox.askyesno("Confirmar Remoção", f"Remover '{self.selecionados[sku]['nome']}' do carrinho?", parent=janela)
            if confirm:
                del self.selecionados[sku]
                tree.delete(iid)
                self.atualizar_total()

        btn_frame = tk.Frame(janela)
        btn_frame.pack(pady=5)

        tk.Button(btn_frame, text="Editar Quantidade", command=editar_quantidade, bg="#007acc", fg="white").pack(side="left", padx=5)
        tk.Button(btn_frame, text="Remover Produto", command=remover_produto, bg="#cc3300", fg="white").pack(side="left", padx=5)
        tk.Button(btn_frame, text="Fechar", command=janela.destroy).pack(side="left", padx=5)

    def atualizar_total(self):
        total = sum(item["total"] for item in self.selecionados.values())
        self.label_total.config(text=f"total: R$ {total:.2f}")

    def realizar_venda(self):
        if not self.selecionados:
            messagebox.showwarning("Atenção", "Nenhum produto selecionado!")
            return

        for item in self.selecionados.values():
            sucesso = self.db.ajustar_quantidade(item["sku"], -item["quantidade_vendida"])
            if not sucesso:
                messagebox.showerror("Erro", f"Erro ao vender '{item['nome']}'.")
                return

        self.hist.registrar_venda(list(self.selecionados.values()))
        total = sum(i["total"] for i in self.selecionados.values())
        messagebox.showinfo("Venda Realizada", f"Venda concluída! total: R$ {total:.2f}")
        self.root.destroy()
        nova_root = tk.Tk()
        AppMenuInicial(nova_root)
        nova_root.mainloop()

    def voltar(self):
        self.root.destroy()
        nova_root = tk.Tk()
        AppMenuInicial(nova_root)
        nova_root.mainloop()


#Janela controle de caixa
class AppControleCaixa:
    def __init__(self, root):
        self.root = root
        self.root.title("Controle de Caixa")
        self.db = EstoqueCSV()
        self.hist = HistoricoVendas()

        try:
            self.root.state("zoomed")
        except tk.TclError:
            self.root.attributes("-fullscreen", True)
            def sair_fullscreen(event):
                self.root.attributes("-fullscreen", False)
            self.root.bind("<Escape>", sair_fullscreen)

        self.frame = tk.Frame(root)
        self.frame.pack(padx=10, pady=10, fill="both", expand=True)

        tk.Label(self.frame, text="Resumo de Vendas por Data", font=("Arial", 16, "bold")).pack(pady=10)

        colunas = ["Data_Venda", "Total Vendido (R$)", "Lucro (R$)"]
        self.tree = ttk.Treeview(self.frame, columns=colunas, show="headings")
        for col in colunas:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="center", width=200)
        self.tree.pack(fill="both", expand=True)

        tk.Label(root, text="Clique duas vezes numa data para ver os detalhes.", font=("Arial", 10, "italic")).pack()

        tk.Button(root, text="Voltar ao Menu", command=self.voltar_ao_menu, bg="#cc3300", fg="white").pack(pady=10)

        self.tree.bind("<Double-1>", self.mostrar_detalhes_data)

        self.carregar_resumo()

    def carregar_resumo(self):
        df_vendas = pd.read_csv(self.hist.arquivo)
        df_estoque = self.db.listar_produtos()

        if df_vendas.empty:
            messagebox.showinfo("Sem vendas", "Não há registros de vendas.")
            return

        df_vendas["data_venda"] = df_vendas["data_venda"].astype(str)
        df_vendas = df_vendas[df_vendas["data_venda"] != "nan"]

        datas = df_vendas["data_venda"].unique()

        try:
            datas = pd.to_datetime(datas, errors='coerce')
            datas = datas.dropna()
            datas = sorted(datas)
            datas = [d.strftime("%Y-%m-%d") for d in datas]
        except Exception:
            datas = sorted(datas)

        for data in datas:
            vendas_dia = df_vendas[df_vendas["data_venda"] == data]
            total_vendido = vendas_dia["total"].sum()

            total_compra = 0.0
            for _, venda in vendas_dia.iterrows():
                sku = venda["sku"]
                qtd = venda["quantidade_vendida"]
                produto_estoque = df_estoque[df_estoque["sku"] == sku]
                if not produto_estoque.empty:
                    valor_compra_unit = float(produto_estoque.iloc[0]["valor_compra"])
                else:
                    valor_compra_unit = 0.0
                total_compra += valor_compra_unit * qtd

            lucro = total_vendido - total_compra
            self.tree.insert("", tk.END, values=(data, f"{total_vendido:.2f}", f"{lucro:.2f}"))

    def mostrar_detalhes_data(self, event):
        item = self.tree.focus()
        if not item:
            return
        dados = self.tree.item(item)["values"]
        if not dados:
            return
        data_selecionada = dados[0]
        DetalhesCaixa(self.root, data_selecionada, self.db, self.hist)

    def voltar_ao_menu(self):
        self.root.destroy()
        nova_root = tk.Tk()
        AppMenuInicial(nova_root)
        nova_root.mainloop()

class DetalhesCaixa:
    def __init__(self, parent, data_venda, db, hist):
        self.janela = tk.Toplevel(parent)
        self.janela.title(f"Detalhes de Vendas - {data_venda}")
        self.janela.geometry("800x500")

        self.db = db
        self.hist = hist
        self.data_venda = data_venda

        tk.Label(self.janela, text=f"Produtos vendidos em {data_venda}", font=("Arial", 14, "bold")).pack(pady=10)

        colunas = ["sku", "nome", "quantidade_vendida", "preco_unitario", "valor_total", "fornecedor", "valor_compra_unitario", "venda_id"]
        self.tree = ttk.Treeview(self.janela, columns=colunas, show="headings")
        for col in colunas:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="center", width=100)
        self.tree.pack(fill="both", expand=True)

        tk.Button(self.janela, text="Fechar", command=self.janela.destroy, bg="#cc3300", fg="white").pack(pady=10)

        self.carregar_detalhes()

    def carregar_detalhes(self):
        df_vendas = pd.read_csv(self.hist.arquivo)
        df_estoque = self.db.listar_produtos()

        df_vendas_data = df_vendas[df_vendas["data_venda"] == self.data_venda]

        cores = [
                    "#73f873",  
                    "#526bdb",  
                    "#e4e13f",  
                    "#e24f4f",
                    "#8b32da",
                    "#3fdbe4",  
                    "#ff7b00",
                    "#f54291", 
                    "#00d98c",  
                    "#b32d00",  
                    "#6c00c3",  
                    "#00b4d8",  
                    "#ffd000",  
                    "#ff3f3f",  
                    "#44ff00",  
                ]

        id_cores = {}
        cor_index = 0

        for _, venda in df_vendas_data.iterrows():
            sku = venda["sku"]
            qtd = venda["quantidade_vendida"]
            preco_unit = venda["preco_unitario"]
            valor_total = venda["total"]
            venda_id = venda.get("venda_id", "")

            produto_estoque = df_estoque[df_estoque["sku"] == sku]
            if not produto_estoque.empty:
                valor_compra_unit = float(produto_estoque.iloc[0]["valor_compra"])
                fornecedor = produto_estoque.iloc[0]["fornecedor"]
            else:
                valor_compra_unit = 0.0
                fornecedor = "Desconhecido"

            tag = f"venda_{venda_id}"
            if tag not in id_cores:
                id_cores[tag] = cores[cor_index % len(cores)]
                cor_index += 1
            self.tree.insert("", tk.END, values=(
                sku,
                venda["nome"],
                qtd,
                f"R$ {preco_unit:.2f}",
                f"R$ {valor_total:.2f}",
                fornecedor,
                f"R$ {valor_compra_unit:.2f}",
                venda_id
            ), tags=(tag,))

        for tag, cor in id_cores.items():
            self.tree.tag_configure(tag, background=cor)


#Janela do menu principal
class AppMenuInicial:
    def __init__(self, root):
        self.root = root
        self.root.title("Sistema de Controle")
        self.root.geometry("400x350")
        self.centralizar_janela()

        frame = tk.Frame(root, bg="#f0f8ff")
        frame.pack(expand=True)

        tk.Label(frame, text="Bem-Vindo(a)", font=("Arial", 16, "bold"), bg="#f0f8ff").pack(pady=20)

#Botões
        tk.Button(frame, text="Controle de estoque", font=("Arial", 12),
                  command=self.abrir_estoque, bg="#007acc", fg="white", width=20).pack(pady=10)

        tk.Button(frame, text="Controle de Vendas", font=("Arial", 12),
                  command=self.abrir_vendas, bg="#28a745", fg="white", width=20).pack(pady=10)

        tk.Button(frame, text="Controle de Caixa", font=("Arial", 12),
                  command=self.abrir_caixa, bg="#ffcc00", fg="black", width=20).pack(pady=10)

        tk.Button(frame, text="Sair", font=("Arial", 12),
                  command=self.root.destroy, bg="#cc3300", fg="white", width=20).pack(pady=10)

    def centralizar_janela(self):
        self.root.update_idletasks()
        largura = 400
        altura = 350
        x = (self.root.winfo_screenwidth() // 2) - (largura // 2)
        y = (self.root.winfo_screenheight() // 2) - (altura // 2)
        self.root.geometry(f"{largura}x{altura}+{x}+{y}")

    def abrir_estoque(self):
        self.root.destroy()
        nova_root = tk.Tk()
        AppEstoque(nova_root)
        nova_root.mainloop()

    def abrir_vendas(self):
        self.root.destroy()
        nova_root = tk.Tk()
        AppVendas(nova_root)
        nova_root.mainloop()

    def abrir_caixa(self):
        self.root.destroy()
        nova_root = tk.Tk()
        AppControleCaixa(nova_root)
        nova_root.mainloop()

#Roda o software
if __name__ == "__main__":
    root = tk.Tk()
    AppMenuInicial(root)
    root.mainloop()
