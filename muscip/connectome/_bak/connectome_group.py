from . import connectome as con

class TNConnectomeGroup(object):
    """Group of connectomes with built-in functions for group
    analysis.

    """

    def __init__(self,
                 subject_dir=None,     # path to directory containing subjects
                 subjects=None,        # list of subjects
                 connectome_path=None  # path to append to
                                       # subject_dir/subject/... to
                                       # realise complete path to
                                       # connectome

    ):
        import os.path as op
        self.subject_dir = op.abspath(subject_dir)
        self.subjects = subjects
        self.connectome_path = connectome_path
        self._info_keys = None
        self._metric_keys = None
        self._number_of_nodes = None

    @property
    def info_keys(self):
        if self._info_keys:
            return self._info_keys
        else:
            self.load_info_keys()
            return self._info_keys
        
    @property
    def metric_keys(self):
        if self._metric_keys:
            return self._metric_keys
        else:
            self.load_metric_keys()
            return self._metric_keys

    @property
    def number_of_nodes(self):
        if self._number_of_nodes:
            return self._number_of_nodes
        else:
            self.guess_number_of_nodes()
            return self._number_of_nodes
            
    def connectomes(self):
        """Iterate and yield connectomes."""
        try:
            for subject in self.subjects:
                from os.path import join
                yield con.read_gpickle(join(self.subject_dir,
                                            subject,
                                            self.connectome_path))
        except Exception as e:
            raise e

    def export_to_matlab(self, filename,
                         number_of_nodes=None,
                         subnetwork_nodes=None):
        structure = dict()
        structure['Sub'] = list()
        exclude_keys = ['streamlines', 'streamlines_length']
        if number_of_nodes is None:
            number_of_nodes = self.number_of_nodes
        for connectome in self.connectomes():
            # grab info for connectome
            record = dict()
            for key in self.info_keys:
                try:
                    record[key] = connectome.graph['info'][key]
                except KeyError:
                    record[key] = None
            # grab metrics for connectome
            for key in self.metric_keys:
                if key in exclude_keys:
                    continue
                if subnetwork_nodes is None:
                    record[key] = connectome.matrix_for_key(key,
                                                            number_of_nodes=number_of_nodes)
                else:
                    record[key] = connectome.submatrix_for_key(subnetwork_nodes, key)
            structure['Sub'].append(record)
            from scipy.io import savemat
            savemat(filename, structure)
        
    def dataFrame(self, info_keys=None, metric_keys=None, number_of_nodes=None):
        try:
            df = dict()
            import numpy as np

            # if info keys is none...assume we want them all
            if not info_keys:
                info_keys = list()
                for C in self.connectomes():
                    try:
                        for key in C.graph['info'].keys():
                            if key not in info_keys:
                                info_keys.append(key)
                    except Exception as e:
                        raise e
                    
            for C in self.connectomes():
                for key in info_keys:
                    try:
                        if key not in df.keys():
                            df[key] = list()
                        df[key].append(C.graph['info'][key])
                    except KeyError:
                        continue
                    except Exception as e:
                        raise e
                for key in metric_keys:
                    try:
                        if key not in df.keys():
                            df[key] = list()
                        df[key].append(C.matrix_for_key(key))
                    except KeyError:
                        continue
                    except Exception as e:
                        raise e
            import pandas
            return pandas.DataFrame(df)
        except Exception as e:
            raise e
        
    def visualize_adj_matrix(self,
                             function=None,
                             group_key=None,
                             metric_key=None,
                             number_of_nodes=None,
                             zero_diagonal=True,
                             binarize=False,
                             fixed_density=None
    ):
        pass

    def load_info_keys(self):
        self._info_keys = list()
        for C in self.connectomes():
            try:
                for key in C.graph['info']:
                    if key not in self._info_keys:
                        self._info_keys.append(key)
            except KeyError:
                continue
            except Exception, e:
                raise e
        self._info_keys.sort()

    def load_metric_keys(self):
        self._metric_keys = list()
        try:
            for C in self.connectomes():
                for u,v,data in C.edges_iter(data=True):
                    for key in data.keys():
                        if key not in self._metric_keys:
                            self._metric_keys.append(key)
        except Exception, e:
            raise e
        self._metric_keys.sort()

    def guess_number_of_nodes(self):
        guess = 0
        for connectome in self.connectomes():
            max_node = max(connectome.nodes())
            if max_node > guess:
                guess = max_node
        return guess

    def set_info(self, csvfile, id_key, new_filename=None):
        
            import os.path as op
            from copy import copy
            # create the csv reader and grab data
            try:
                import csv
                read_info = dict()
                f = open(op.abspath(csvfile), 'rt')
                reader = csv.DictReader(f)
                for record in reader:
                    read_info[record[id_key]] = record
            except Exception, e:
                print e
            finally:
                f.close()
            # for every connectome entry, try and get info from the info we
            # previously read
            for idx, C in enumerate(self.connectomes()):
                # try to get info for subject
                try:
                    subject = self.subjects[idx]
                    new_info = read_info[subject]
                except KeyError:
                    print "No info found in csv file for: %s" % subject
                    continue
                # apply new info
                C.set_info(new_info)
                # try to save connectome
                try:
                    if new_filename:
                        outpath = op.join(self.subject_dir, subject,
                                          op.dirname(self.connectome_path),
                                          new_filename)
                    else:
                        outpath = op.join(self.subject_dir, subject, self.connectome_path)
                    C.write(outpath)
                except Exception, e:
                    print "Could not save connectome file -- %s" % e
